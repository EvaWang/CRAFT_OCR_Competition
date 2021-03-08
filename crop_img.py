from PIL import Image

import argparse
import os

def cropImg(img, position, save_path):
    # img = Image.open('./images/9_update.jpg')
    img = img.copy()
    img = img.crop(position).convert("RGB")
    img.save(save_path)

def read_positions(pos_filepath):

    file1 = open(pos_filepath, 'r')
    count = 0
    pos = []
    while True:
        count += 1
    
        # Get next line from file
        line = file1.readline()
        
        # if line is empty
        # end of file is reached
        if not line:
            break
        # print("Line{}: {}".format(count, line.strip()))
        
        arr = line.strip().split(',')
        arr = [int(i) for i in arr]
        left = min(arr[0], arr[2], arr[4], arr[6])
        top = min(arr[1], arr[3], arr[5], arr[7])
        right = max(arr[0], arr[2], arr[4], arr[6])
        bottom = max(arr[1], arr[3], arr[5], arr[7])

        pos.append((left, top, right, bottom))
        # cropImg((left, top, right, bottom), f'test_{count}')
    
    file1.close()
    return pos


def _parse_args():
    parser = argparse.ArgumentParser(description='Extract Char From CRAFT Text Detection')
    # 原圖位置
    parser.add_argument('--ori_file_folder', default='./competition/Training_Set/tif', type=str, help='filename')
    # 辨識txt檔案位置
    parser.add_argument('--result_folder', default='./competition/test0306', type=str, help='folder path to input images')
    # 存擋位置
    parser.add_argument('--cropimg_folder', default='./competition/test0306/extract', type=str, help='folder path to input images')

    args = parser.parse_args()
    return args

if __name__ == '__main__':

    args = _parse_args()

    if not os.path.isdir(args.cropimg_folder):
        os.mkdir(args.cropimg_folder)

    # Using readline()
    target_files = [f for f in os.listdir(args.ori_file_folder) if os.path.isfile(os.path.join(args.ori_file_folder, f))]
    
    for t_file in target_files:
        sp_filename = t_file.split('.')
        pos_filepath = os.path.join(args.result_folder, f"res_{sp_filename[0]}.txt")
        positions = read_positions(pos_filepath)

        img = Image.open(os.path.join(args.ori_file_folder, t_file))
        count = 0
        for pos in positions:
            save_path = pos_filepath = os.path.join(args.cropimg_folder, f"res_{sp_filename[0]}_{count}.jpg")
            cropImg(img, pos, save_path)
            count = count+1
