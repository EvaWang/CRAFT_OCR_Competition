from typing import Dict
from PIL import Image

from operator import itemgetter
import argparse
import os
from tqdm import tqdm

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
    parser.add_argument('--result_folder', default='./competition/Craft_result', type=str, help='folder path to input images')
    # 存擋位置
    parser.add_argument('--cropimg_folder', default='./competition/extract', type=str, help='folder path to input images')

    args = parser.parse_args()
    return args

def sort_position_list(pos_list):
    been_sort = []
    sort_list = {}
    line_number = 0
    while not len(been_sort) == len(pos_list):
        x_max = 0
        x_min = 0
        for i, pos in enumerate(pos_list):
            if pos[2] > x_max and not i in been_sort:
                # 框字的左右界
                x_max = pos[2]
                x_min = pos[0]

        line_temp = []
        for i, pos in enumerate(pos_list):
            # 中心落在左右界內
            center_in = (pos[2] + pos[0])/2 > x_min and (pos[2] + pos[0])/2 < x_max
            right_in = pos[2]>x_min
            if not i in been_sort and (center_in or right_in):
            # if not i in been_sort and (pos[2] + pos[0])/2 > x_min and (pos[2] + pos[0])/2 < x_max:
                line_temp.append((i, pos[1]))
                been_sort.append(i)

        line_temp = sorted(line_temp, key=lambda elem: elem[1])
        sort_list[line_number] = [word_pos[0] for word_pos in line_temp]
        line_number += 1
    return sort_list


def sortByCoordinated(pos_list):
    sorted_list = sorted(pos_list, key=lambda p: p[2])

    # (left, top, right, bottom)
    # (   0,   1,     2,      3)

    line_count = 0
    ordered_line = dict()
    right_most =  sorted_list[-1]# find upper left point
    x_min, x_max = right_most[0], right_most[2]
    while len(sorted_list)>0:
        # print(f'line:{line_count}, 範圍:{x_min}:{x_max}')
        # 有重疊 而且有一角在裡面
        if (right_most[2]<=x_max and right_most[2]>=x_min) or (right_most[0]<=x_max and right_most[0]>=x_min):
            # 沒事 同一行
            pass
        else:
            line_count = line_count+1
            x_min = min(right_most[0], x_min)
            x_max = max(right_most[2], x_max)

        getLine = ordered_line.get(line_count, [])
        getLine.append(right_most)
        ordered_line.update({line_count: getLine})
        # ordered_line.append((line_count, right_most))
        sorted_list.pop()
        if len(sorted_list)==0: break
        right_most = sorted_list[-1]

        # sorted(ordered_line, key=lambda p: p[1][1])

    # 校正高度
    return_list = []
    for line_key in ordered_line:
        ordered_words = sorted(ordered_line[line_key], key=lambda p: p[1])
        previous_pos = ordered_words[0]
        return_list.append((line_key, previous_pos))
        for word_idx in range(1, len(ordered_words)):
            # 4 case,
            # sordered_words左上角落在前一個內
            # sordered_words左下角落在前一個內
            # sordered_words高低跨越前一個
            # sordered_words高低被前一個包含在內
            if (ordered_words[word_idx][1]>=previous_pos[1] and ordered_words[word_idx][1]<=previous_pos[3]) or \
               (ordered_words[word_idx][3]>=previous_pos[1] and ordered_words[word_idx][3]<=previous_pos[3]) or \
               (ordered_words[word_idx][1]>=previous_pos[1] and ordered_words[word_idx][3]<=previous_pos[3]) or \
               (ordered_words[word_idx][1]<=previous_pos[1] and ordered_words[word_idx][3]>=previous_pos[3]):
               #高度有重疊
                overlap_top = max(ordered_words[word_idx][1], previous_pos[1])
                overlap_btm = min(ordered_words[word_idx][3], previous_pos[3])
                overlap_height = (overlap_btm - overlap_top)/(previous_pos[3] - previous_pos[1])
                # 先右再左
                if abs(overlap_height)>0.5 and (previous_pos[2]<ordered_words[word_idx][2]):
                    return_list.pop()
                    return_list.append((line_key, ordered_words[word_idx]))
                    return_list.append((line_key, previous_pos))
                else:
                    return_list.append((line_key, ordered_words[word_idx]))
            else:
                return_list.append((line_key, ordered_words[word_idx]))

            previous_pos = ordered_words[word_idx]

    return return_list

def rect_Overlap(l1, r1, l2, r2): 
      
    # If one rectangle is on left side of other 
    if(l1.x >= r2.x or l2.x >= r1.x): 
        return False
  
    # If one rectangle is above other 
    if(l1.y <= r2.y or l2.y <= r1.y): 
        return False
  
    return True

if __name__ == '__main__':

    args = _parse_args()

    if not os.path.isdir(args.cropimg_folder):
        os.mkdir(args.cropimg_folder)

    # Using readline()
    target_files = [f for f in os.listdir(args.ori_file_folder) if os.path.isfile(os.path.join(args.ori_file_folder, f))]
    # target_files = target_files[1:2]
    
    for t_file in tqdm(target_files):
        sp_filename = t_file.split('.')
        pos_filepath = os.path.join(args.result_folder, f"res_{sp_filename[0]}.txt")
        positions = read_positions(pos_filepath)

        # positions = sortByCoordinated(positions)

        # positions = [positions[0], positions[-1]]


        # for pos in positions:
        #     print(pos)
        
        # img = Image.open(os.path.join(args.ori_file_folder, t_file))
        # count = 0
        # for pos in positions:
        #     print(pos)
        #     save_path = pos_filepath = os.path.join(args.cropimg_folder, f"res_{sp_filename[0]}_{count}.jpg")
        #     cropImg(img, pos, save_path)
        #     count = count+1


        # sort_list = sort_position_list(positions)
        # img = Image.open(os.path.join(args.ori_file_folder, t_file))
        # for line_key in sort_list:
        #     print(f"Line:{line_key}")
        #     for word in sort_list[line_key]:
        #         pos = positions[word]
        #         print(f"{word}:{pos}")
        #         save_path = pos_filepath = os.path.join(args.cropimg_folder, f"res_{sp_filename[0]}_{line_key}_{word}.jpg")
        #         cropImg(img, pos, save_path)

        positions = sortByCoordinated(positions)
        count = 0
        img = Image.open(os.path.join(args.ori_file_folder, t_file))
        for line_key, pos in positions:
            save_path = pos_filepath = os.path.join(args.cropimg_folder, f"res_{sp_filename[0]}_{line_key}_{count}.jpg")
            cropImg(img, pos, save_path)
            count = count+1
