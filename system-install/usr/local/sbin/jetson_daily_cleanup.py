#!/usr/bin/env python3

import argparse
import datetime
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Generator

import cv2


datefmt_glob = "[0-9]" * 8    # * 8 for YYYYMMDD


def create_movie_from_images(image_folder: Path, output_video_path: Path, frame_rate: int):
    """
    Create a video from PNG images in a folder, embedding timestamps from filenames.
    
    Parameters:
    - image_folder: Path to the folder containing PNG images.
    - output_video_path: Path to save the output video file.
    - frame_rate: Frame rate for the output video.
    """
    cur_t = 0.0
    count_frames = 0
    frame_delay = round(1 / frame_rate, 3)
    with tempfile.NamedTemporaryFile(mode="w+t", encoding="utf-8", suffix=".txt") as fp_cmd, \
            tempfile.NamedTemporaryFile(mode="w+t", encoding="utf-8", suffix=".txt") as fp_frames:
        for img in sorted(image_folder.glob("*.png")):
            hour_time_millis = img.name[-14:-4]
            hour_time = hour_time_millis[:6]
            try:
                cur_time = datetime.datetime.strptime(hour_time, "%H%M%S").time()
            except ValueError:
                print(f"skipping invalid png name format: {img.name}")
                continue
            fp_frames.write(f"file {img.as_posix()}\n")
            escaped_cur_time = str(cur_time).replace(":", "\\:")
            fp_cmd.write(
                f"{round(cur_t, 3)}-{round(cur_t + frame_delay, 3)} [enter] drawtext reinit 'text={escaped_cur_time}';\n"
            )
            count_frames += 1
            cur_t += frame_delay
        fp_frames.flush()
        fp_cmd.flush()
        output_video_path.unlink(missing_ok=True)
        cmd_args = (
            "ffmpeg",
            '-r', f"{frame_rate}",
            "-f", "concat",
            "-safe", "0",
            '-i', fp_frames.name,
            '-vf',
            f"sendcmd=f={fp_cmd.name},"
            "drawtext=text=''"
            ':fontcolor=blue:fontsize=36'
            ':x=(w-text_w)/2'
            ':y=(h-text_h)/8',
            '-c:v', 'libx264', "-pix_fmt", "yuv420p",
            output_video_path.as_posix(),
        )
        try:
            subprocess.check_call(cmd_args, cwd=image_folder)
        except subprocess.CalledProcessError as err:
            print(f"Failed to run ffmpeg on {image_folder}: {err}")
            # sys.exit(0)
            return 0
        else:
            print(f"created {output_video_path}")
            # sys.exit(0)
            return count_frames


def validate_and_cleanup(image_folder: Path, video_path: Path, frm_ct: int):
    """
    Validate the created video and delete PNG files if validation succeeds.
    
    Parameters:
    - video_path: Path to the created video file.
    - image_folder: Path to the folder containing the original PNG files.
    
    Returns:
    - None (Performs validation and file deletion).
    """
    # Count the number of PNG files in the folder
    image_files = sorted(image_folder.glob("*.png"))
    if frm_ct == 0:
        # print("No PNG files found in the image folder.")
        return False

    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        if os.path.isfile(video_path):
            print(f"Error: Cannot open video file {video_path}. The file might be corrupt.")
        else:
            print(f"Error: {video_path} does not exist.")
        return False

    # Get the total number of frames in the video
    num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Number of frames in the video: {num_frames}")
    print(f"Number of PNG files: {frm_ct}")

    # Compare the number of frames to the number of PNG files
    if num_frames != frm_ct:
        print("Validation failed: The number of frames does NOT match the number of PNG files.")
        return False

    print("Validation successful: The number of frames matches the number of PNG files.")

    # Optional: Confirm that the video is viewable by displaying the first frame
    ret, frame = cap.read()
    # Release the video capture object
    cap.release()
    if not ret:
        print("Error: Unable to read frames from the video. The video might be corrupt.")
        return False

    # Delete PNG files
    print("Deleting PNG files...")
    for image_file in image_files:
        try:
            os.remove(image_file)
        except Exception as e:
            print(f"Error deleting {image_file}: {e}")
    print("All PNG files deleted successfully.")
    return True


def find_web_image_directories(start_dir: Path) -> Generator[Tuple[Path, List[Path]], None, None]:
    """
    Find all subdirectories under the given starting directory
    that end with '_web_images'.
    
    Parameters:
    - start_dir: The starting directory to search from.
    
    Returns:
    - A generator of [top_dir, web_image_dirs], where `top_dir` is the first level top dir (YYYYMMDD),
     and `web_image_dirs` is a (sorted) list of the found web image dirs under it.
    """
    for top_dir in sorted(start_dir.glob(datefmt_glob)):
        if not top_dir.is_dir():
            continue
        web_image_dirs = []
        for path in top_dir.glob(f"*/*/{datefmt_glob}*_web_images"):
            if not path.is_dir():
                continue
            web_image_dirs.append(path)
        yield top_dir, sorted(web_image_dirs)


class Executor:

    def __init__(
        self,
        *,
        start_directory: Path,
        target_dir: Path,
        delete_older_days: int,
        stop_days_before_now: int,
        frame_rate: int,
    ):
        self.start_dir = start_directory
        self.target_dir = target_dir
        self.delete_older_days = delete_older_days
        self.stop_days_before_now = stop_days_before_now
        self.frame_rate = frame_rate
        self.today = datetime.date.today()

    def sync(self, rel_parent: Path):
        assert not rel_parent.is_absolute()
        print(f"syncing {rel_parent}")
        dest_parent = self.target_dir.joinpath(rel_parent)
        dest_parent.mkdir(parents=True, exist_ok=True)
        rsync_args = [
            'rsync',
            '-av',  # before the other --no
            # target network does not allow to set anything but content:
            '--no-owner', '--no-group', '--no-times', '--no-perms',
            '--size-only',  # check on file size to decide (re)transfer/copy or not.
            self.start_dir.joinpath(rel_parent).as_posix() + "/",  # ensure the start dir ends with /
            dest_parent.as_posix().rstrip("/"),  # ensure the dest dir does NOT end with /
            #                                    # see rsync man.
        ]
        # print(rsync_args)
        try:
            subprocess.check_call(rsync_args)
        except subprocess.CalledProcessError as err:
            print(f"failed sync {rel_parent} to {self.target_dir}: {err}")
            return

    @staticmethod
    def _on_delete_error(func, p, exc_info):
        print(f"Error deleting {p}: {exc_info}")

    def clean(self, path: Path):
        print(f"Removing {path}")
        shutil.rmtree(path, onerror=self._on_delete_error)

    def process_image_folder(self, image_folder: Path):
        has_png = any(image_folder.glob("*.png"))
        if not has_png:
            return
        print(f" doing {image_folder.name}")
        name = image_folder.name.replace("_images", "_video") + ".mp4"
        output_video_path = image_folder.joinpath(name)
        frm_ct = create_movie_from_images(image_folder, output_video_path, self.frame_rate)
        if frm_ct > 0:
            validate_and_cleanup(image_folder, output_video_path, frm_ct)

    def execute(self):
        max_up_to = self.today - datetime.timedelta(days=self.stop_days_before_now)
        if self.delete_older_days <= 0:
            print("Not removing old files when delete_older_days is <= 0")
            min_date_keep = None
        else:
            min_date_keep = self.today - datetime.timedelta(days=self.delete_older_days)
        #
        for top_dir, web_image_dirs in find_web_image_directories(self.start_dir):
            rel_top = top_dir.relative_to(self.start_dir)
            print(f"processing {rel_top}")
            try:
                date_top_dir = datetime.datetime.strptime(rel_top.name[:8], '%Y%m%d').date()
            except ValueError:
                print(f"skipping invalid {rel_top}")
                continue
            if date_top_dir >= max_up_to:
                print(f"Skipping too recent top data dir: {rel_top}")
                continue
            for image_folder in web_image_dirs:
                self.process_image_folder(image_folder)
            self.sync(rel_top)
            if min_date_keep is not None and date_top_dir < min_date_keep:
                self.clean(top_dir)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--raw-data-local-dir", help="RawDataLocal dir",
                        type=Path,
                        default=Path.home().joinpath("Documents", "RawDataLocal"))
    parser.add_argument("--target-dir", help="Target dir, RawDataLocal as well",
                        type=Path,
                        default=Path('/mnt/isilon/Data/JetsonAutoTrainer/RawDataLocal'))
    parser.add_argument("--stop-days-before-now", type=int, default=0,
                        help="Do not process data more recent than n days before current date")
    parser.add_argument("--delete-older-days", type=int, default=0,
                        help="Delete any trial data (YYYYMMDD) older than this number of days. 0 or lower to disable.")
    parser.add_argument("--web-fps", type=int, default=10,
                        help="FPS for generated web images video.")

    args = parser.parse_args()

    print(f"args={args}")

    executor = Executor(
        start_directory=args.raw_data_local_dir,
        target_dir=args.target_dir,
        delete_older_days=args.delete_older_days,
        stop_days_before_now=args.stop_days_before_now,
        frame_rate=args.web_fps,
    )
    executor.execute()
    print("Finished")


if __name__ == '__main__':
    main()
