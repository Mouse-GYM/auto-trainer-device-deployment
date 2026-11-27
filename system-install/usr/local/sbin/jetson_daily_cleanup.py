#!/usr/bin/env python3

import argparse
import collections
import dataclasses
import datetime
import enum
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Iterator, List, NamedTuple, Optional, Sequence, Tuple

# Imported defensively so a broken venv is still reported in the status file instead of crashing at import.
try:
    import cv2
except ImportError:
    cv2 = None


DATE_DIR_GLOB = "[0-9]" * 8
WEB_IMAGES_SUFFIX = "_web_images"
FRAME_NAME_RE = re.compile(r"_(\d{6})_(\d{3})\.png$")
DEFAULT_STATUS_FILE = Path.home() / ".config" / "Colorado" / "nightly_maintenance_status.json"
STATUS_SCHEMA_VERSION = 1
MAX_LISTED_FILES = 20


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def write_text_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def stage_text(path: Path, text: str) -> Path:
    staged = path.with_name(path.name + ".partial")
    staged.write_text(text, encoding="utf-8")
    return staged


class RunReport:
    """Errors and warnings of one run, published as the JSON status file other services poll."""

    def __init__(self, status_file: Path):
        self.status_file = status_file
        self.started_at = now_iso()
        self.errors: List[dict] = []
        self.warnings: List[dict] = []

    def add_error(self, kind: str, path: Optional[Path], message: str) -> None:
        self.errors.append({"kind": kind, "path": None if path is None else str(path), "message": message})
        print(f"ERROR [{kind}] {'-' if path is None else path}: {message}")

    def add_warning(self, kind: str, path: Path, message: str, files: Sequence[Path]) -> None:
        self.warnings.append({
            "kind": kind,
            "path": str(path),
            "message": message,
            "count": len(files),
            "files": [f.name for f in files[:MAX_LISTED_FILES]],
        })
        print(f"WARNING [{kind}] {path}: {message}")

    def start(self) -> None:
        self._write(self._payload("running", None, None))

    def finish(self, exit_code: Optional[int] = None) -> int:
        code = exit_code if exit_code is not None else (1 if self.errors else 0)
        written = self._write(self._payload("success" if code == 0 else "failure", code, now_iso()))
        print(f"Finished: {len(self.errors)} errors, {len(self.warnings)} warnings, exit code {code}, "
              f"status in {self.status_file}")
        return code if written else max(code, 1)

    def _payload(self, result: str, exit_code: Optional[int], finished_at: Optional[str]) -> dict:
        return {
            "schema_version": STATUS_SCHEMA_VERSION,
            "result": result,
            "exit_code": exit_code,
            "started_at": self.started_at,
            "finished_at": finished_at,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def _write(self, payload: dict) -> bool:
        try:
            write_text_atomically(self.status_file, json.dumps(payload, indent=2) + "\n")
        except OSError as err:
            # Recorded before finish() builds its payload, so a later successful write still says failure.
            self.add_error("status-write-failed", self.status_file, str(err))
            return False
        return True


class Frame(NamedTuple):
    path: Path
    time: datetime.time
    stamp: str  # HHMMSS_mmm, as written to the timestamps file


@dataclasses.dataclass
class FrameSelection:
    frames: List[Frame] = dataclasses.field(default_factory=list)
    bad_names: List[Path] = dataclasses.field(default_factory=list)
    unreadable: List[Path] = dataclasses.field(default_factory=list)


def parse_frame_name(name: str) -> Optional[Tuple[datetime.time, str]]:
    match = FRAME_NAME_RE.search(name)
    if match is None:
        return None
    hhmmss, millis = match.groups()
    try:
        time = datetime.datetime.strptime(hhmmss, "%H%M%S").time()
    except ValueError:
        return None
    return time, f"{hhmmss}_{millis}"


def select_frames(pngs: Sequence[Path]) -> FrameSelection:
    assert cv2 is not None, "only called when conversion is enabled"
    selection = FrameSelection()
    for png in pngs:
        parsed = parse_frame_name(png.name)
        if parsed is None:
            selection.bad_names.append(png)
        elif png.stat().st_size == 0 or cv2.imread(str(png), cv2.IMREAD_UNCHANGED) is None:
            selection.unreadable.append(png)
        else:
            selection.frames.append(Frame(png, *parsed))
    return selection


def concat_list(frames: Sequence[Frame]) -> str:
    lines = []
    for frame in frames:
        escaped = frame.path.as_posix().replace("'", "'\\''")
        lines.append(f"file '{escaped}'\n")
    return "".join(lines)


def sendcmd_script(frames: Sequence[Frame], fps: int) -> str:
    # With an input -r, ffmpeg stamps frame i at exactly i/fps; deriving each interval from the index
    # (rather than summing a rounded step) keeps every label on its own frame at any frame rate.
    lines = []
    for i, frame in enumerate(frames):
        label = frame.time.strftime("%H\\:%M\\:%S")
        lines.append(f"{i / fps:.6f}-{(i + 1) / fps:.6f} [enter] drawtext reinit 'text={label}';\n")
    return "".join(lines)


def timestamps_text(frames: Sequence[Frame]) -> str:
    return "".join(f"{i}\t{frame.stamp}\n" for i, frame in enumerate(frames))


def encode_video(ffmpeg: str, frames: Sequence[Frame], output: Path, fps: int) -> Optional[str]:
    """Encode `frames` into `output`; return an error message, or None on success."""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt") as concat_file, \
            tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt") as cmd_file:
        concat_file.write(concat_list(frames))
        concat_file.flush()
        cmd_file.write(sendcmd_script(frames, fps))
        cmd_file.flush()
        args = [
            ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-r", str(fps), "-f", "concat", "-safe", "0", "-i", concat_file.name,
            "-vf", f"sendcmd=f={cmd_file.name},drawtext=text='':fontcolor=blue:fontsize=36"
                   ":x=(w-text_w)/2:y=(h-text_h)/8",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            # The output is a .partial name, whose extension names no container.
            "-f", "mp4", str(output),
        ]
        try:
            proc = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, universal_newlines=True)
        except OSError as err:
            return f"could not run {ffmpeg}: {err}"
    if proc.returncode != 0:
        output_text = proc.stdout or ""
        print(output_text, end="")
        tail = [line for line in output_text.splitlines() if line.strip()][-3:]
        return f"ffmpeg exited with status {proc.returncode}: " + " | ".join(tail)
    return None


def validate_video(path: Path, expected: Optional[int]) -> Optional[str]:
    """Return why `path` is not a usable video of `expected` frames (any count when None), or None."""
    assert cv2 is not None, "only called when conversion is enabled"
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            return "cannot open video"
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if expected is not None and frames != expected:
            return f"video has {frames} frames, expected {expected}"
        ok, _ = cap.read()
        if not ok:
            return "cannot read the first frame of the video"
    finally:
        cap.release()
    return None


def video_frame_count(path: Path) -> int:
    assert cv2 is not None, "only called when conversion is enabled"
    cap = cv2.VideoCapture(str(path))
    try:
        return int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        cap.release()


def iter_top_dirs(start_dir: Path) -> Iterator[Path]:
    """Yield every YYYYMMDD directory under `start_dir`, including those without web-image folders,
    which still need syncing and cleanup."""
    for path in sorted(start_dir.glob(DATE_DIR_GLOB)):
        if path.is_dir():
            yield path


def find_web_image_dirs(top_dir: Path) -> List[Path]:
    """Return the web-image folders under `top_dir` at any depth: continuous (hourly) capture writes
    `<date>/<device>/<date>_<device>_hNN_web_images`, trial capture `<date>/<device>/trialNNN/…_web_images`."""
    return sorted(p for p in top_dir.rglob(DATE_DIR_GLOB + "*" + WEB_IMAGES_SUFFIX) if p.is_dir())


class FolderResult(enum.Enum):
    CONVERTED = "converted"
    ALREADY_CONVERTED = "already converted"
    NO_IMAGES = "no images"
    NO_USABLE_FRAMES = "no usable frames"
    UNVERIFIED = "unverified video"
    PUBLISH_FAILED = "publish failed"
    FAILED = "failed"


class Executor:

    def __init__(
        self,
        *,
        start_directory: Path,
        target_dir: Path,
        delete_older_days: int,
        stop_days_before_now: int,
        frame_rate: int,
        report: RunReport,
        today: Optional[datetime.date] = None,
    ):
        self.start_dir = start_directory
        self.target_dir = target_dir
        self.delete_older_days = delete_older_days
        self.stop_days_before_now = stop_days_before_now
        self.frame_rate = frame_rate
        self.report = report
        self.today = today or datetime.date.today()
        self.ffmpeg: Optional[str] = None

    @property
    def can_convert(self) -> bool:
        return self.ffmpeg is not None and cv2 is not None

    def check_prerequisites(self) -> bool:
        """Return False when the run must not touch any data."""
        try:
            # Listing also triggers the share's systemd automount; a failed mount is any OSError, not just ENOENT.
            with os.scandir(self.target_dir) as entries:
                next(entries, None)
        except OSError as err:
            self.report.add_error("target-unavailable", self.target_dir, str(err))
            return False
        self.ffmpeg = shutil.which("ffmpeg")
        if self.ffmpeg is None:
            self.report.add_error("ffmpeg-missing", None,
                                  "ffmpeg is not on PATH; web-image videos are not created this run")
        if cv2 is None:
            self.report.add_error("opencv-missing", None,
                                  "OpenCV (cv2) cannot be imported; web-image videos are not created this run")
        return True

    def sync(self, rel_top: Path) -> bool:
        assert not rel_top.is_absolute()
        print(f"syncing {rel_top}")
        top = self.start_dir.joinpath(rel_top)
        dest_parent = self.target_dir.joinpath(rel_top)
        rsync_args = [
            'rsync',
            '-av',  # before the other --no
            # target network does not allow to set anything but content:
            '--no-owner', '--no-group', '--no-times', '--no-perms',
            '--size-only',  # check on file size to decide (re)transfer/copy or not.
            '--exclude=*.partial',  # never publish a half-written video or timestamps file from an interrupted conversion
            top.as_posix() + "/",  # ensure the start dir ends with /
            dest_parent.as_posix().rstrip("/"),  # ensure the dest dir does NOT end with / (see rsync man)
        ]
        try:
            dest_parent.mkdir(parents=True, exist_ok=True)
            subprocess.check_call(rsync_args)
        except subprocess.CalledProcessError as err:
            self.report.add_error("sync-failed", top, f"rsync exited with status {err.returncode}")
            return False
        except OSError as err:
            self.report.add_error("sync-failed", top, str(err))
            return False
        return True

    def clean(self, path: Path) -> None:
        print(f"Removing {path}")
        failures: List[str] = []
        shutil.rmtree(path, onerror=lambda func, p, exc_info: failures.append(f"{p}: {exc_info[1]}"))
        if failures:
            self.report.add_error("delete-failed", path,
                                  f"{len(failures)} entries could not be deleted; first: {failures[0]}")

    def _report_exclusions(self, folder: Path, selection: FrameSelection) -> None:
        if selection.bad_names:
            self.report.add_warning(
                "bad-filename", folder,
                f"{len(selection.bad_names)} PNG files have names without a _HHMMSS_mmm.png timestamp; "
                "left in place and synced",
                selection.bad_names)
        if selection.unreadable:
            self.report.add_warning(
                "unreadable-image", folder,
                f"{len(selection.unreadable)} PNG files are empty or cannot be decoded; left in place and synced",
                selection.unreadable)

    def _report_not_in_video(self, folder: Path, frames: Sequence[Frame]) -> None:
        if frames:
            self.report.add_warning(
                "not-in-video", folder,
                f"{len(frames)} PNG files are not in the folder's existing video; left in place and synced",
                [f.path for f in frames])

    def _existing_video_result(self, folder: Path, video: Path, timestamps: Path,
                               selection: FrameSelection) -> Optional[FolderResult]:
        """Decide what an existing final video means; None means convert the folder again.

        Never encodes, deletes or overwrites anything."""
        if timestamps.exists():
            expected = sum(1 for line in timestamps.read_text(encoding="utf-8").splitlines() if line.strip())
            reason = validate_video(video, expected)
            if reason is None:
                self._report_not_in_video(folder, selection.frames)
                return FolderResult.ALREADY_CONVERTED
            print(f" {video.name} is not a validated conversion ({reason}); converting again")
            return None

        # Only the 6d40b5d/b98ea17 test builds left a video without a timestamps file: they kept their output
        # on any failure (possibly readable but short) and deleted every PNG on success.
        reason = validate_video(video, None)
        if reason is not None:
            print(f" {video.name} is not a validated conversion ({reason}); converting again")
            return None
        frames = video_frame_count(video)
        made = video.stat().st_mtime
        older = [f for f in selection.frames if f.path.stat().st_mtime < made]
        if not older:
            self._report_not_in_video(folder, selection.frames)
            return FolderResult.ALREADY_CONVERTED
        if len(older) >= frames:
            print(f" {video.name} has {frames} frames and {len(older)} older PNG files remain; converting again")
            return None
        self.report.add_error(
            "unverified-video", folder,
            f"{video.name} has no timestamps file and {frames} frames, but only {len(older)} PNG files older "
            "than it remain; video and PNGs left in place. Delete the video to have the folder converted again.")
        return FolderResult.UNVERIFIED

    def process_image_folder(self, folder: Path) -> FolderResult:
        video = folder / (folder.name[: -len("_images")] + "_video.mp4")
        partial = video.with_name(video.name + ".partial")
        timestamps = folder / f"{folder.name}_timestamps.txt"
        staged = timestamps.with_name(timestamps.name + ".partial")

        # Leftovers of a run killed mid-conversion.
        partial.unlink(missing_ok=True)
        staged.unlink(missing_ok=True)

        pngs = sorted(folder.glob("*.png"))
        if not pngs:
            return FolderResult.ALREADY_CONVERTED if video.exists() else FolderResult.NO_IMAGES
        print(f" doing {folder.name}")
        selection = select_frames(pngs)
        self._report_exclusions(folder, selection)

        if video.exists():
            result = self._existing_video_result(folder, video, timestamps, selection)
            if result is not None:
                return result
        if not selection.frames:
            return FolderResult.NO_USABLE_FRAMES

        assert self.ffmpeg is not None
        kind = "encode-failed"
        error = encode_video(self.ffmpeg, selection.frames, partial, self.frame_rate)
        if error is None:
            kind = "validation-failed"
            error = validate_video(partial, len(selection.frames))
        if error is not None:
            partial.unlink(missing_ok=True)
            self.report.add_error(kind, folder, error)
            return FolderResult.FAILED

        # Both renames must succeed before any PNG is deleted. Any exception here becomes PUBLISH_FAILED, which
        # stops this top directory from syncing: rsync has no --delete, so a copy of an older timestamps file
        # already on the share would otherwise end up beside the new video.
        published = False
        try:
            staged = stage_text(timestamps, timestamps_text(selection.frames))
            # A new video must never sit beside a timestamps file from another conversion.
            timestamps.unlink(missing_ok=True)
            os.replace(partial, video)
            os.replace(staged, timestamps)
            published = True
        except Exception as err:
            self.report.add_error("publish-failed", folder, f"{type(err).__name__}: {err}")
        finally:
            for leftover in (partial, timestamps.with_name(timestamps.name + ".partial")):
                try:
                    leftover.unlink(missing_ok=True)
                except OSError as err:
                    self.report.add_error("delete-failed", leftover, str(err))
        if not published:
            return FolderResult.PUBLISH_FAILED

        failed = []
        for frame in selection.frames:
            try:
                frame.path.unlink()
            except OSError as err:
                failed.append(f"{frame.path.name}: {err}")
        if failed:
            self.report.add_error("delete-failed", folder,
                                  f"{len(failed)} PNG files could not be deleted; first: {failed[0]}")
        print(f" created {video.name} from {len(selection.frames)} frames")
        return FolderResult.CONVERTED

    def execute(self) -> None:
        if not self.check_prerequisites():
            return
        max_up_to = self.today - datetime.timedelta(days=self.stop_days_before_now)
        if self.delete_older_days <= 0:
            print("Not removing old files when delete_older_days is <= 0")
            min_date_keep = None
        else:
            min_date_keep = self.today - datetime.timedelta(days=self.delete_older_days)

        for top_dir in iter_top_dirs(self.start_dir):
            rel_top = top_dir.relative_to(self.start_dir)
            print(f"processing {rel_top}")
            try:
                date_top_dir = datetime.datetime.strptime(top_dir.name, '%Y%m%d').date()
            except ValueError:
                print(f"skipping invalid {rel_top}")
                continue
            if date_top_dir >= max_up_to:
                print(f"Skipping too recent top data dir: {rel_top}")
                continue

            results: "collections.Counter[FolderResult]" = collections.Counter()
            if self.can_convert:
                for folder in find_web_image_dirs(top_dir):
                    try:
                        result = self.process_image_folder(folder)
                    except Exception as err:
                        traceback.print_exc()
                        self.report.add_error("folder-failed", folder, f"{type(err).__name__}: {err}")
                        result = FolderResult.FAILED
                    results[result] += 1
                summary = ", ".join(f"{count} {result.value}" for result, count in results.items())
                print(f"{rel_top}: {summary or 'no web-image folders'}")
            else:
                print(f"{rel_top}: video conversion disabled")

            if results[FolderResult.PUBLISH_FAILED]:
                print(f"{rel_top}: not synced this run; a folder's video and timestamps file are mid-replacement")
                continue
            if self.sync(rel_top) and min_date_keep is not None and date_top_dir < min_date_keep:
                self.clean(top_dir)


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError(f"must be greater than 0, got {value}")
    return number


def non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError(f"must not be negative, got {value}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, allow_abbrev=False)
    parser.add_argument("--raw-data-local-dir", help="RawDataLocal dir",
                        type=Path,
                        default=Path.home().joinpath("Documents", "RawDataLocal"))
    parser.add_argument("--target-dir", help="Target dir, RawDataLocal as well",
                        type=Path,
                        default=Path('/mnt/isilon/Data/JetsonAutoTrainer/RawDataLocal'))
    parser.add_argument("--stop-days-before-now", type=non_negative_int, default=0,
                        help="Do not process data more recent than n days before current date")
    parser.add_argument("--delete-older-days", type=int, default=0,
                        help="Delete any trial data (YYYYMMDD) older than this number of days. 0 or lower to disable.")
    parser.add_argument("--web-fps", type=positive_int, default=10,
                        help="FPS for generated web images video.")
    parser.add_argument("--status-file", type=Path, default=DEFAULT_STATUS_FILE,
                        help="JSON file describing the latest run, for other services to poll.")
    return parser


def status_file_from_argv(argv: Sequence[str]) -> Path:
    """Find the status file without argparse, so that an earlier valid --status-file survives a later malformed
    one that makes the full parse fail. Must match the wrapper's scan in auto_trainer_nightly_maintenance.sh."""
    status_file = DEFAULT_STATUS_FILE
    for i, arg in enumerate(argv):
        if arg == "--status-file" and i + 1 < len(argv) and not argv[i + 1].startswith("-"):
            status_file = Path(argv[i + 1])
        elif arg.startswith("--status-file=") and len(arg) > len("--status-file="):
            status_file = Path(arg[len("--status-file="):])
    return status_file


def main(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    report = RunReport(status_file_from_argv(argv))
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exit_:
        if not exit_.code:
            raise
        report.add_error("invalid-arguments", None, "invalid command-line arguments; usage is in the journal")
        return report.finish(2)

    print(f"args={args}")
    report.start()
    try:
        Executor(
            start_directory=args.raw_data_local_dir,
            target_dir=args.target_dir,
            delete_older_days=args.delete_older_days,
            stop_days_before_now=args.stop_days_before_now,
            frame_rate=args.web_fps,
            report=report,
        ).execute()
    except Exception as err:
        traceback.print_exc()
        report.add_error("unexpected-exception", None, f"{type(err).__name__}: {err}")
    return report.finish()


if __name__ == '__main__':
    sys.exit(main())
