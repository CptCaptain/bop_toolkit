from PIL import Image, ImageDraw
import json
import torch
import numpy as np
from pathlib import Path
from collections import defaultdict

img_id = "14190"

# use newly generated data, complete with squirrel
new_data = True
# use annotations as generated by BlenderProc (as in, not further processed)
use_blenderproc_anns = True


if new_data:
    base_path = Path('/home/nils/datasets/bop/output/bop_data/ycbv')
else:
    base_path = Path('/media/Data1/BOP/ycb-v/ycbv')
im_path = base_path /'train'/'train_pbr'

scene_id = int(img_id) // 1000
im_id = int(img_id) - scene_id*1000

if use_blenderproc_anns:
    with open(f'{im_path}/{scene_id:06}/scene_gt_info.json', 'r') as f:
        anns = json.load(f)
    with open(f'{im_path}/{scene_id:06}/scene_gt.json', 'r') as f:
        infos = json.load(f)
else:
    im_anns = defaultdict(list)
    with open(base_path/'annotations/train.json', 'r') as f:
        annotations = json.load(f)
        print(f"{annotations.keys()=}")
        for ann in annotations['annotations']:
            im_anns[ann['image_id']].append(ann['id'])

im = Image.open(f'{im_path}/{scene_id:06}/rgb/{im_id:06}.jpg')


def get_color(depth_component):
    # Calculate the color intensity based on the depth_component (z-value)
    intensity = int(255 * abs(depth_component))
    return (intensity, 0, 255 - intensity) if depth_component > 0 else (0, intensity, 255 - intensity)


def visualize_rotation_axis(image, rotation_matrix, bounding_box):
    # Load the image
    draw = ImageDraw.Draw(image)

    # Convert the bounding box coordinates to integers
    x1, y1, x2, y2 = map(int, bounding_box)

    # Compute the center of the bounding box
    center = torch.tensor([(x1 + x2) / 2, (y1 + y2) / 2], dtype=torch.float32)

    # Define the rotation axis in the object's local coordinate system
    rotation_axis_local = torch.tensor([0, 0, 1], dtype=torch.float32)


    # Transform the rotation axis to the image coordinate system
    rotation_axis_image = torch.matmul(rotation_matrix, rotation_axis_local)

    # Scale the rotation axis and translate it to the bounding box center
    scale = max(x2 - x1, y2 - y1) / 2
    rotation_axis_image_scaled = center + scale * rotation_axis_image[:2]

    # Get the color of the line based on the depth_component (z-value)
    depth_color = get_color(rotation_axis_image[2].item())

    # Draw the bounding box and rotation axis
    draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
    draw.line([tuple(center.numpy()), tuple(rotation_axis_image_scaled.numpy())], fill=depth_color, width=2)

    return image


def draw_bboxes(im: Image, anns: list, infos: list):
    d = ImageDraw.Draw(im)
    for ann, inf in zip(anns, infos):
        try:
            x0, y0, w, h = ann['bbox_obj']
        except:
            x0, y0, w, h = ann['bbox']
        x1, y1 = x0 + w, y0 + h
        d.text((x0, y0), str(inf['obj_id']))
        rot_mat = torch.tensor(inf['cam_R_m2c']).reshape([3,3])
        visualize_rotation_axis(im, rot_mat, [x0, y0, x1, y1])
    
if use_blenderproc_anns:
    draw_bboxes(im, anns[str(im_id)], infos[str(im_id)])
else:
    anns = [annotations['annotations'][ann_id] for ann_id in im_anns[int(img_id)]]
    infos = [{
        'obj_id': ann['category_id'],
        'cam_R_m2c': ann['relative_pose']['rotation'],
        } for ann in anns]
    draw_bboxes(im, anns, infos)

im.save('/home/nils/poet_gt_squirrel_selfvis.png')

