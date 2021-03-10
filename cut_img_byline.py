import cv2
from PIL import Image,ImageDraw
from skimage.feature import peak_local_max
import numpy as np

import argparse
import os
from tqdm import tqdm


def find_line_btw_words(filepath, save_path):
    ori_image = Image.open(filepath)
    draw_img = ori_image.copy()
    draw = ImageDraw.Draw(draw_img)
    
    for pos in positions:
        # 把文字框塗白
        draw.rectangle([pos[0], pos[1], pos[2], pos[3]], fill="WHITE")

    # 切掉沒有框字的部分
    draw_img = draw_img.crop((min_left,min_top, max_right,max_btm))
    grayImage = cv2.cvtColor(np.asarray(draw_img), cv2.COLOR_BGR2GRAY)
    ret, th1 = cv2.threshold(grayImage, 254, 255, cv2.THRESH_BINARY)
    # 加總x軸上的值並正規化, white 255, black 0
    sum_gray = np.sum(th1, axis=0)
    sum_gray = (sum_gray-sum_gray.min())/(sum_gray.max()-sum_gray.min())

    #抓local-min，掃描寬度為平均字寬
    seperation_idx = peak_local_max(-sum_gray, min_distance=int(avg_width/2))
    seperation_idx = seperation_idx.squeeze()

    print(avg_width)
    selected_idx = [seperation_idx[0]+min_left]
    draw_check = ImageDraw.Draw(ori_image)
    for idx in range(len(seperation_idx)-1):
        pos_x = seperation_idx[idx]+min_left
        if seperation_idx[idx]-seperation_idx[idx+1] !=1:
            if (selected_idx[-1]-pos_x) < (avg_width/2):
                print(selected_idx[-1]-pos_x)
                print(f"check:{pos_x}")
                continue
            selected_idx.append(pos_x)
            draw_check.line((pos_x, 0, pos_x, ori_image.size[1]), fill=(0,255,0,5), width=10)
    
    draw_check.line((seperation_idx[0]+min_left, 0, seperation_idx[0]+min_left, ori_image.size[1]), fill=(0,255,0,5), width=10)
    draw_check.line((seperation_idx[-1]+min_left, 0, seperation_idx[-1]+min_left, ori_image.size[1]), fill=(0,255,0,5), width=10)
    ori_image.convert("RGB").thumbnail((600,600))
    ori_image.save(save_path)

    selected_idx.append(seperation_idx[-1]+min_left)

    print(selected_idx)

    pass


def read_positions(pos_filepath):

    file1 = open(pos_filepath, 'r')
    count = 0
    pos = []
    collect_left=[]
    collect_right=[]
    collect_top=[]
    collect_btm=[]
    collect_width=[]
    while True:
        count += 1
    
        # Get next line from file
        line = file1.readline()
        
        # if line is empty
        # end of file is reached
        if not line:
            break
        
        arr = line.strip().split(',')
        arr = [int(i) for i in arr]
        left = min(arr[0], arr[2], arr[4], arr[6])
        top = min(arr[1], arr[3], arr[5], arr[7])
        right = max(arr[0], arr[2], arr[4], arr[6])
        bottom = max(arr[1], arr[3], arr[5], arr[7])

        pos.append((left, top, right, bottom))
        collect_left.append(left)
        collect_right.append(right)
        collect_top.append(top)
        collect_btm.append(bottom)
        collect_width.append(right-left)
    
    file1.close()
    
    avg_width = np.average(collect_width)
    return pos, min(collect_left), max(collect_right), min(collect_top), max(collect_btm), avg_width

def _parse_args():
    parser = argparse.ArgumentParser(description='Extract Char From CRAFT Text Detection')
    # 原圖位置
    parser.add_argument('--ori_file_folder', default='./competition/Training_Set/tif', type=str, help='filename')
    # 辨識txt檔案位置
    parser.add_argument('--result_folder', default='./competition/Craft_result', type=str, help='folder path to input images')
    # parser.add_argument('--result_folder', default='/nfs/home/evawang/youtube_crawler/CRAFT-pytorch/result', type=str, help='folder path to input images')
    # 存擋位置
    parser.add_argument('--cropimg_folder', default='./competition/extract_test', type=str, help='folder path to input images')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = _parse_args()

    if not os.path.isdir(args.cropimg_folder):
        os.mkdir(args.cropimg_folder)

    target_files = [f for f in os.listdir(args.ori_file_folder) if os.path.isfile(os.path.join(args.ori_file_folder, f))]
    target_files = target_files[16:17]


    for t_file in tqdm(target_files):
        sp_filename = t_file.split('.')
        pos_filepath = os.path.join(args.result_folder, f"res_{sp_filename[0]}.txt")
        positions, min_left, max_right, min_top, max_btm, avg_width = read_positions(pos_filepath)
        
        ori_filepath = os.path.join(args.ori_file_folder, t_file)
        save_path = os.path.join(args.cropimg_folder, f"{sp_filename[0]}.jpg")
        find_line_btw_words(ori_filepath, save_path)
      
