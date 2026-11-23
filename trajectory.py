import json

# Load GT
with open(r'e:\duan64\duan64_2\annotation\data\tracking_ground_truth.json', 'r') as f:
    data = json.load(f)

gt_028 = None
for d in data:
    if d['global_id'] == 'GT_028':
        gt_028 = d
        break

print("GT_028 trajectory (showing every 10th frame):")
frames = sorted(gt_028['frames'], key=lambda x: x['frame_id'])
for f in frames[::10]:
    print(f"  Frame {f['frame_id']}: center={f['center']}, visibility={f['visibility']}")
print(f"  ... (total {len(frames)} frames)")

# Also check GT_014 and GT_024 for comparison
print("\nGT_024 (overlaps with GT_028, ends at 289):")
gt_024 = [d for d in data if d['global_id'] == 'GT_024'][0]
frames_024 = sorted(gt_024['frames'], key=lambda x: x['frame_id'])
print(f"  First: frame {frames_024[0]['frame_id']}, center={frames_024[0]['center']}")
print(f"  Last: frame {frames_024[-1]['frame_id']}, center={frames_024[-1]['center']}")

print("\nGT_014 (motorcycle on right):")
gt_014 = [d for d in data if d['global_id'] == 'GT_014'][0]
frames_014 = sorted(gt_014['frames'], key=lambda x: x['frame_id'])
print(f"  First: frame {frames_014[0]['frame_id']}, center={frames_014[0]['center']}")
print(f"  Last: frame {frames_014[-1]['frame_id']}, center={frames_014[-1]['center']}")
