import cv2
from PIL import Image,ImageDraw
from skimage.feature import peak_local_max
import numpy as np

import argparse
import os
from tqdm import tqdm

# 先左再右 先小再大
def overlap_rate(define_range, target, is_horizontal=True):
    # range_w = define_range[1]-define_range[0]
    target_w = target[1]-target[0]
    overlap_w = 0
    if is_horizontal:
        if target[1]<=define_range[0] and target[0]<=define_range[0]:
            return 0 # 沒有重疊
    else:
        if  (target[1]<=define_range[0] and target[0]<=define_range[0]) or \
            (target[0]>=define_range[1] and target[1]>=define_range[1]):
            return 0 # 沒有重疊

    overlap_w = (min(define_range[1], target[1])-max(define_range[0], target[0]))/target_w
    return abs(overlap_w)

def cropImg(img, position, save_path):
    img = img.copy()
    img = img.crop(position).convert("RGB")
    img.save(save_path)

def sort_word_byline(column_idx, positions):
    column_idx.append(0) # 加入最左邊
    right_max = sorted(positions, key=lambda p: p[2])[-1][2]
    sorted_list = []
    select_col = 0
    while select_col < len(column_idx):
        # 從右邊開始
        current_col = column_idx[select_col]
        # print(f"{current_col},{right_max}")
        # 左偏、右偏、完全在內、寬於範圍
        # 算覆蓋率
        words = [ (select_col, (left, top, right, btm)) for left, top, right, btm in positions if 0.6 < overlap_rate((current_col,right_max),(left,right))]
        words = sorted(words, key=lambda p: p[1][3]) # 依高度排

        if len(words)==0: 
            select_col = select_col +1
            right_max = current_col
            continue

        # 依高度掃 預設有兩個 沒有就左邊放NONE
        ordered_byHeight = [[None, words[0]]]
        positions.remove(words[0][1])
        for idx in range(1, len(words)):
            r = overlap_rate((words[idx-1][1][1], words[idx-1][1][3]), (words[idx][1][1], words[idx][1][3]), False)
            if r>0.5:
                right = words[idx-1]
                left =  words[idx]
                if words[idx-1][1][2] < words[idx][1][2]:
                    right = words[idx]
                    left = words[idx-1]
                ordered_byHeight[-1] = [left, right]
            else:
                ordered_byHeight.append([None, words[idx]])
            positions.remove(words[idx][1])

        queue = []
        for left_w, right_w in ordered_byHeight:
            if left_w == None:
                sorted_list = sorted_list + queue
                queue = []
            else: queue.append(left_w)
            sorted_list.append(right_w)
       
        if len(queue)>0:
            sorted_list = sorted_list + queue

        select_col = select_col +1
        right_max = current_col

    return sorted_list

def find_line_btw_words(ori_image, save_path, positions, min_left, max_right, min_top, max_btm, avg_width, debug=False):
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

    # print(f"avg:{avg_width}")
    selected_idx = [seperation_idx[0]+min_left]
    for idx in range(1, len(seperation_idx)):
        pos_x = seperation_idx[idx]+min_left
        if seperation_idx[idx-1]-seperation_idx[idx] !=1:
            if len(selected_idx)>0 and (selected_idx[-1]-pos_x) < avg_width:
                # print(f"selected_idx[-1]:{selected_idx[-1]}, diff:{selected_idx[-1]-pos_x}")
                continue
            # else:print("selected_idx[-1]:None")
            selected_idx.append(pos_x)

    if debug:
        draw_check_img = ori_image.copy()
        draw_check = ImageDraw.Draw(draw_check_img)
        for pos in positions:
            draw_check.rectangle([pos[0], pos[1], pos[2], pos[3]], outline="RED", width=10)

        for s in selected_idx:
            draw_check.line((s, 0, s, ori_image.size[1]), fill=(0,255,0,5), width=10)
        draw_check_img.convert("RGB").thumbnail((600,600))
        draw_check_img.save(save_path)

    # print(selected_idx)
    return selected_idx

def read_positions(pos_filepath):

    file1 = open(pos_filepath, 'r')
    pos = []
    collect_left=[]
    collect_right=[]
    collect_top=[]
    collect_btm=[]
    collect_width=[]
    not_divied = []
    while True:
        line = file1.readline()
        if not line:
            break
        
        arr = line.strip().split(',')
        arr = [int(i) for i in arr]
        left = min(arr[0], arr[2], arr[4], arr[6])
        top = min(arr[1], arr[3], arr[5], arr[7])
        right = max(arr[0], arr[2], arr[4], arr[6])
        bottom = max(arr[1], arr[3], arr[5], arr[7])

        width = right-left
        height = bottom-top

        ratio = height/width
        if ratio > 1.6:
            not_divied.append((left, top, right, bottom))
        else:
            pos.append((left, top, right, bottom))
            collect_left.append(left)
            collect_right.append(right)
            collect_top.append(top)
            collect_btm.append(bottom)
            collect_width.append(width)

    file1.close()
    
    avg_width = np.average(collect_width)
    for d in not_divied:
        if (d[2]-d[0])>avg_width*0.5:
            pos.append((d[0], d[1], d[2], int(0.5*(d[1]+d[3]))))
            pos.append((d[0], int(0.5*(d[1]+d[3])),  d[2], d[3]))
            
    return pos, min(collect_left), max(collect_right), min(collect_top), max(collect_btm), avg_width

def _parse_args():
    parser = argparse.ArgumentParser(description='Extract Char From CRAFT Text Detection')
    parser.add_argument('--ori_file_folder', default='./competition/Training_Set/tif', type=str, help='原圖位置')
    parser.add_argument('--result_folder', default='./competition/Craft_result', type=str, help='辨識txt檔案位置')
    parser.add_argument('--cropimg_folder', default='./competition/extract_20', type=str, help='存擋位置')
    parser.add_argument('--debug', default=False, type=bool, help='draw debug images')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = _parse_args()

    if not os.path.isdir(args.cropimg_folder):
        os.mkdir(args.cropimg_folder)

    target_files = [f for f in os.listdir(args.ori_file_folder) if os.path.isfile(os.path.join(args.ori_file_folder, f))]
    # mock test
    target_files = target_files[19:20]

    char_img_arr = []
    for t_file in tqdm(target_files):
        sp_filename = t_file.split('.')
        pos_filepath = os.path.join(args.result_folder, f"res_{sp_filename[0]}.txt")
        positions, min_left, max_right, min_top, max_btm, avg_width = read_positions(pos_filepath)
        
        save_path = os.path.join(args.cropimg_folder, f"{sp_filename[0]}.jpg")
        img = Image.open(os.path.join(args.ori_file_folder, t_file))
        # 依直欄切分
        selected_idx = find_line_btw_words(img, save_path, positions, min_left, max_right, min_top, max_btm, avg_width, debug=args.debug)
        sorted_list = sort_word_byline(selected_idx, positions)
        count = 0
        for line_key, pos in sorted_list:
            folder = args.cropimg_folder
            if args.debug:
                folder = os.path.join(args.cropimg_folder, f"{line_key}")
                if not os.path.isdir(folder):
                    os.mkdir(folder)

            save_path = os.path.join(folder, f"res_{sp_filename[0]}_{line_key:03d}_{count:03d}.jpg")
            cropImg(img, pos, save_path)

            # if args.debug: cropImg(img, pos, save_path)
            
            # img = img.copy()
            # img = img.crop(pos)
            
            # char_img_arr.append(img)

            count = count+1
