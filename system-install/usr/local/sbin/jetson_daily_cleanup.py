#!/usr/bin/env python3

import argparse
import datetime
import os
import shutil
import subprocess
from pathlib import Path
from typing import List

import cv2
import sys


def create_movie_from_images(image_folder, output_video_path, frame_rate):
    """
    Create a video from PNG images in a folder, embedding timestamps from filenames.
    
    Parameters:
    - image_folder: Path to the folder containing PNG images.
    - output_video_path: Path to save the output video file.
    - frame_rate: Frame rate for the output video.
    """
    # print(f"Reading images from {image_folder}")
    curr_frm = 0
    
    # Get list of PNG files and sort by filename
    image_files = sorted(image_folder.glob("*.png"))
    if not image_files:
        # print("No PNG files found in the specified folder.")
        return 0

    # Get the dimensions of the first image for video properties
    for image_file in image_files:
        sample_image = cv2.imread(image_file)
        if sample_image is not None:
            height, width, _ = sample_image.shape
            break
        # elif image_file == image_files[-1]:
    else:
        print(f"No valid images from {image_folder}")
        return curr_frm

    # Define the codec and initialize VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # For .mp4 files
    video_writer = cv2.VideoWriter(output_video_path, fourcc, frame_rate, (width, height))
    ts_list = []
    for image_file in image_files:
        # Read the image
        frame = cv2.imread(image_file)
        if frame is None:
            continue
        
        # Extract timestamp from filename (assuming format includes hh:mm:ss)
        filename = os.path.basename(image_file)
        # Example assumes timestamp in the format "image_hh-mm-ss.png"
        # timestamp = filename.split('_')[-1].split('.')[0].replace('-', ':')
        timestamp = filename.split('_')[-2]  # Extract hhmmss part
        formatted_timestamp = f"{timestamp[:2]}:{timestamp[2:4]}:{timestamp[4:]}"  # Convert to hh:mm:ss
        millis = filename.split('_')[-1]  # Extract hhmmss part
        ts_list.append((curr_frm,f"{timestamp}_{millis[:-4]}"))
        curr_frm += 1

        # Embed timestamp as text in the frame
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        font_color = (255, 255, 255)  # White
        thickness = 2
        position = (10, 30)  # Top-left corner (x, y)
        cv2.putText(frame, formatted_timestamp, position, font, font_scale, font_color, thickness, cv2.LINE_AA)

        # Write the frame to the video
        video_writer.write(frame)

    # Release the video writer
    video_writer.release()
    
    # Write all timestamps to .txt file
    
    fileID = os.path.basename(image_folder) + '_timestamps.txt'
    file_path = os.path.join(image_folder, fileID)
    with open(file_path, 'w') as file:
        for ts in ts_list:
            file.write(f"{ts[0]}\t{ts[1]}\n")
            
    print(f"Video saved to {output_video_path}")
    return curr_frm


def validate_and_cleanup(image_folder, video_path, frm_ct):
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


def find_data_dirs(start_dir: Path) -> List[Path]:
    dirs = []
    for path in start_dir.glob("[0-9]" * 8):  # * 8 for YYYYMMDD
        if path.is_dir():
            dirs.append(path)
    return dirs


def find_web_image_directories(start_dir: Path, *, before_date: datetime.date) -> List[Path]:
    """
    Find all subdirectories under the given starting directory
    that end with '_web_images'.
    
    Parameters:
    - start_dir: The starting directory to search from.
    
    Returns:
    - A list of paths to directories ending with '_web_images'.
    """
    web_image_dirs = []
    
    # Traverse the directory tree
    for root, dirs, files in os.walk(start_dir):
        root = Path(root)
        for directory in dirs:
            date_front = directory[:8]
            if not (date_front.isdigit() and directory.endswith('_web_images')):
                # print(f"Skipping non-matching YYYYMMDD and _web_images dir: {directory}")
                continue
            date_images = datetime.datetime.strptime(date_front, '%Y%m%d').date()
            if date_images >= before_date:
                print(f"Skipping too recent data dir: {directory}")
                continue
            image_folder = root.joinpath(directory)
            has_image_files = any(image_folder.glob("*.png"))
            has_mp4_files = any(image_folder.glob("*.mp4"))
            if has_image_files or has_mp4_files:
                web_image_dirs.append(image_folder)
    return web_image_dirs


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
    parser.add_argument("--delete-older-days", type=int, default=14,
                        help="Delete any trial data (YYYYMMDD) older than this number of days")

    args = parser.parse_args()

    start_directory = args.raw_data_local_dir

    today = datetime.date.today()
    max_up_to = today - datetime.timedelta(days=args.stop_days_before_now)

    data_dirs = find_data_dirs(start_directory)

    web_image_dirs = find_web_image_directories(start_directory, before_date=max_up_to)

    validated_dirs = []
    for image_folder in web_image_dirs:
        name = image_folder.name.replace("_images", "_video")
        name += ".mp4"
        output_video_path = image_folder.joinpath(name)

        frame_rate = 30
        frm_ct = create_movie_from_images(image_folder, output_video_path, frame_rate)
        if frm_ct > 0:
            if validate_and_cleanup(image_folder, output_video_path, frm_ct):
                validated_dirs.append(image_folder)
        else:
            has_mp4 = any(image_folder.glob("*.mp4"))
            if has_mp4:
                print(f"{image_folder} has no images but has mp4, including")
                validated_dirs.append(image_folder)

    final_dirs = set()

    for validated_dir in validated_dirs:
        rel_parent = validated_dir.relative_to(start_directory).parent
        final_dirs.add(rel_parent)

    final_dirs = sorted(final_dirs)

    for rel_parent in final_dirs:
        print(f"syncing {rel_parent}")
        dest_parent = args.target_dir.joinpath(rel_parent)
        dest_parent.mkdir(parents=True, exist_ok=True)
        rsync_args = [
            'rsync',
            '-av',  # before the other --no
            # target network does not allow to set anything but content:
            '--no-owner', '--no-group', '--no-times', '--no-perms',
            '--size-only',  # check on file size to decide (re)transfer/copy or not.
            start_directory.joinpath(rel_parent).as_posix() + "/",  # ensure the start dir ends with /
            dest_parent.as_posix().rstrip("/"),  # ensure the dest dir does NOT end with /
            #                                    # see rsync man.
        ]
        # print(rsync_args)
        subprocess.check_call(rsync_args)

    # delete older than :
    delete_older_days = args.delete_older_days
    def on_delete_error(func, p, exc_info):
        print(f"Error deleting {p}: {exc_info}")

    if delete_older_days == 0:
        print("Not removing old files when threshold is 0")
    else:
        min_date_keep = today - datetime.timedelta(days=delete_older_days)
        for path in data_dirs:
            dir_date = datetime.datetime.strptime(path.name, "%Y%m%d").date()
            if dir_date < min_date_keep:
                print(f"Removing {path}")
                shutil.rmtree(path, onerror=on_delete_error)

    print("Finished")


if __name__ == '__main__':
    sys.exit(main())
