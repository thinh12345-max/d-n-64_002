"""Custom TrackEval dataset for Project-4 five-class tracking evaluation.

This dataset implements the TrackEval 1.3.0 _BaseDataset interface for the
project's five-class tracking protocol (car, motorcycle, bus, truck, person).

The dataset reads MOT format files produced by the trackeval_adapter and
provides them to TrackEval's CLEAR and Identity metrics.

Reference: D-07.13 feasibility audit, D-07.14 implementation
"""

import csv
import os
from pathlib import Path

import numpy as np

from scipy.optimize import linear_sum_assignment

from trackeval import _timing, utils
from trackeval.utils import TrackEvalException
from trackeval.datasets._base_dataset import _BaseDataset


class Project5ClassDataset(_BaseDataset):
    """Dataset class for Project-4 five-class tracking evaluation.

    Supports evaluation of: car, motorcycle, bus, truck, person

    The dataset reads MOT format files (gt.txt, pred.txt) and seqinfo.ini
    produced by the trackeval_adapter.

    IoU matching is computed using TrackEval's box IoU implementation.
    CLEAR and Identity metrics operate on preprocessed per-class data.
    """

    # Project class mapping (must match trackeval_adapter CLASS_MAPPING)
    CLASS_NAME_TO_ID = {
        "car": 1,
        "motorcycle": 2,
        "bus": 3,
        "truck": 4,
        "person": 5,
    }

    # Valid project classes
    VALID_CLASSES = list(CLASS_NAME_TO_ID.keys())

    @staticmethod
    def get_default_dataset_config():
        """Default class config values.

        This dataset expects data in a specific structure:
        - GT_FOLDER/seqinfo.ini (sequence metadata)
        - GT_FOLDER/gt.txt (ground truth in MOT format)
        - TRACKERS_FOLDER/tracker/pred.txt (predictions in MOT format)
        """
        code_path = utils.get_code_path()
        default_config = {
            "GT_FOLDER": os.path.join(code_path, "data/gt/project5class/"),
            "TRACKERS_FOLDER": os.path.join(code_path, "data/trackers/project5class/"),
            "OUTPUT_FOLDER": None,
            "TRACKERS_TO_EVAL": None,
            "CLASSES_TO_EVAL": ["car", "motorcycle", "bus", "truck", "person"],
            "SPLIT_TO_EVAL": "test",
            "INPUT_AS_ZIP": False,
            "PRINT_CONFIG": True,
            "TRACKER_SUB_FOLDER": "tracker",
            "OUTPUT_SUB_FOLDER": "",
            "TRACKER_DISPLAY_NAMES": None,
            "SEQ_INFO": None,
        }
        return default_config

    def __init__(self, config=None):
        """Initialise dataset.

        Args:
            config: Optional configuration dict. If None, uses default config.
        """
        super().__init__()
        self.config = utils.init_config(
            config, self.get_default_dataset_config(), self.get_name()
        )

        # Set dataset properties
        self.gt_fol = self.config["GT_FOLDER"]
        self.tracker_fol = self.config["TRACKERS_FOLDER"]
        self.should_classes_combine = False
        self.use_super_categories = False
        self.data_is_zipped = self.config["INPUT_AS_ZIP"]

        self.output_fol = self.config["OUTPUT_FOLDER"]
        if self.output_fol is None:
            self.output_fol = self.tracker_fol

        self.tracker_sub_fol = self.config["TRACKER_SUB_FOLDER"]
        self.output_sub_fol = self.config["OUTPUT_SUB_FOLDER"]

        # Validate and set class list
        self.valid_classes = self.VALID_CLASSES
        self.class_list = [
            cls.lower() if cls.lower() in self.valid_classes else None
            for cls in self.config["CLASSES_TO_EVAL"]
        ]
        if not all(self.class_list):
            invalid = [
                cls
                for cls in self.config["CLASSES_TO_EVAL"]
                if cls.lower() not in self.valid_classes
            ]
            raise TrackEvalException(
                f"Invalid classes: {invalid}. Valid classes are: {self.valid_classes}"
            )

        # Store class mapping for use in preprocessing
        self.class_name_to_class_id = self.CLASS_NAME_TO_ID

        # Get sequences to eval
        self.seq_list, self.seq_lengths = self._get_seq_info()

        if len(self.seq_list) < 1:
            raise TrackEvalException("No sequences are selected to be evaluated.")

        # Check GT file exists
        for seq in self.seq_list:
            gt_file = os.path.join(self.gt_fol, seq, "gt.txt")
            if not os.path.isfile(gt_file):
                raise TrackEvalException(f"GT file not found: {gt_file}")

        # Get trackers to eval
        if self.config["TRACKERS_TO_EVAL"] is None:
            self.tracker_list = os.listdir(self.tracker_fol)
        else:
            self.tracker_list = self.config["TRACKERS_TO_EVAL"]

        if self.config["TRACKER_DISPLAY_NAMES"] is None:
            self.tracker_to_disp = dict(zip(self.tracker_list, self.tracker_list))
        elif (self.config["TRACKERS_TO_EVAL"] is not None) and (
            len(self.config["TRACKER_DISPLAY_NAMES"]) == len(self.tracker_list)
        ):
            self.tracker_to_disp = dict(
                zip(self.tracker_list, self.config["TRACKER_DISPLAY_NAMES"])
            )
        else:
            raise TrackEvalException(
                "List of tracker files and tracker display names do not match."
            )

        # Check tracker files exist
        for tracker in self.tracker_list:
            for seq in self.seq_list:
                tracker_file = os.path.join(
                    self.tracker_fol,
                    tracker,
                    self.tracker_sub_fol,
                    seq + ".txt",
                )
                if not os.path.isfile(tracker_file):
                    raise TrackEvalException(f"Tracker file not found: {tracker_file}")

    def _get_seq_info(self):
        """Get sequences and their lengths.

        Reads from seqinfo.ini in GT_FOLDER if SEQ_INFO is not provided.
        """
        seq_list = []
        seq_lengths = {}

        if self.config["SEQ_INFO"]:
            seq_list = list(self.config["SEQ_INFO"].keys())
            seq_lengths = self.config["SEQ_INFO"]
        else:
            # Look for seqinfo.ini in GT_FOLDER
            seqinfo_path = os.path.join(self.gt_fol, "seqinfo.ini")
            if os.path.isfile(seqinfo_path):
                import configparser

                seqinfo = configparser.ConfigParser()
                seqinfo.read(seqinfo_path)

                # Determine sequence name from folder
                seq_name = os.path.basename(self.gt_fol.rstrip(os.sep))
                if seqinfo.has_section("Sequence"):
                    seq_length = int(seqinfo.get("Sequence", "seqLength", fallback=0))
                    if seq_length > 0:
                        seq_list = [seq_name]
                        seq_lengths[seq_name] = seq_length

        # Default to single sequence if no info found
        if not seq_list:
            seq_list = ["seq"]
            seq_lengths = {"seq": 621}  # Default to project frame count

        return seq_list, seq_lengths

    def get_display_name(self, tracker):
        return self.tracker_to_disp[tracker]

    def _load_raw_file(self, tracker, seq, is_gt):
        """Load a file (gt or tracker) in MOT format.

        MOT format: frame, id, x, y, w, h, conf, cls, -1, -1, -1, -1

        If is_gt, returns dict with fields:
            [gt_ids, gt_classes]: list of 1D NDArrays per timestep
            [gt_dets, gt_crowd_ignore_regions]: list of lists of detections
            [gt_extras]: list of dicts with extra info

        If not is_gt, returns dict with fields:
            [tracker_ids, tracker_classes, tracker_confidences]: list of 1D NDArrays
            [tracker_dets]: list of lists of detections
        """
        if is_gt:
            file = os.path.join(self.gt_fol, seq, "gt.txt")
        else:
            file = os.path.join(
                self.tracker_fol, tracker, self.tracker_sub_fol, seq + ".txt"
            )

        num_timesteps = self.seq_lengths[seq]

        # Read MOT format file
        read_data = self._load_mot_file(file, num_timesteps)

        # Convert to required format
        data_keys = ["ids", "classes", "dets"]
        if is_gt:
            data_keys += ["gt_crowd_ignore_regions", "gt_extras"]
        else:
            data_keys += ["tracker_confidences"]
        raw_data = {key: [None] * num_timesteps for key in data_keys}

        # Check for extra timesteps
        current_time_keys = [str(t + 1) for t in range(num_timesteps)]
        extra_time_keys = [x for x in read_data.keys() if x not in current_time_keys]
        if len(extra_time_keys) > 0:
            if is_gt:
                text = "Ground-truth"
            else:
                text = "Tracking"
            raise TrackEvalException(
                f"{text} data contains invalid timesteps: {', '.join(extra_time_keys)}"
            )

        for t in range(num_timesteps):
            time_key = str(t + 1)
            if time_key in read_data.keys():
                time_data = np.asarray(read_data[time_key], dtype=float)

                try:
                    raw_data["dets"][t] = np.atleast_2d(time_data[:, 2:6])
                    raw_data["ids"][t] = np.atleast_1d(time_data[:, 1]).astype(int)
                    raw_data["classes"][t] = np.atleast_1d(time_data[:, 7]).astype(int)
                except IndexError:
                    if is_gt:
                        raise TrackEvalException(
                            f"Cannot load gt data from {file} - not enough columns"
                        )
                    else:
                        raise TrackEvalException(
                            f"Cannot load tracker data from {file} - not enough columns"
                        )

                if not is_gt:
                    raw_data["tracker_confidences"][t] = np.atleast_1d(time_data[:, 6])
            else:
                raw_data["dets"][t] = np.empty((0, 4))
                raw_data["ids"][t] = np.empty(0).astype(int)
                raw_data["classes"][t] = np.empty(0).astype(int)
                if is_gt:
                    raw_data["gt_crowd_ignore_regions"][t] = np.empty((0, 4))
                    raw_data["gt_extras"][t] = {}
                else:
                    raw_data["tracker_confidences"][t] = np.empty(0)

            if is_gt:
                raw_data["gt_crowd_ignore_regions"][t] = np.empty((0, 4))

        # Remap keys
        if is_gt:
            key_map = {
                "ids": "gt_ids",
                "classes": "gt_classes",
                "dets": "gt_dets",
            }
        else:
            key_map = {
                "ids": "tracker_ids",
                "classes": "tracker_classes",
                "dets": "tracker_dets",
            }
        for k, v in key_map.items():
            raw_data[v] = raw_data.pop(k)

        raw_data["num_timesteps"] = num_timesteps
        raw_data["seq"] = seq

        return raw_data

    def _load_mot_file(self, file, num_timesteps):
        """Load MOT format file.

        MOT format: frame, id, x, y, w, h, conf, cls, -1, -1, -1, -1

        Returns:
            dict: {timestep_str: [[frame, id, x, y, w, h, conf, cls, ...], ...]}
        """
        read_data = {}

        if not os.path.isfile(file):
            raise TrackEvalException(f"File not found: {file}")

        with open(file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 8:
                    continue
                try:
                    frame = str(int(float(row[0])))
                    if frame in read_data:
                        read_data[frame].append(row)
                    else:
                        read_data[frame] = [row]
                except (ValueError, IndexError):
                    continue

        return read_data

    @_timing.time
    def get_preprocessed_seq_data(self, raw_data, cls):
        """Preprocess data for a single sequence for a single class.

        Filters detections to only include those of the specified class.
        No distractor handling (project has no distractor classes).

        Args:
            raw_data: Dict from get_raw_seq_data()
            cls: Class name to filter by (e.g., 'car', 'person')

        Returns:
            dict with fields for TrackEval metrics evaluation
        """
        # Check unique IDs
        self._check_unique_ids(raw_data)

        cls_id = self.class_name_to_class_id[cls]

        data_keys = [
            "gt_ids",
            "tracker_ids",
            "gt_dets",
            "tracker_dets",
            "tracker_confidences",
            "similarity_scores",
        ]
        data = {key: [None] * raw_data["num_timesteps"] for key in data_keys}

        unique_gt_ids = []
        unique_tracker_ids = []
        num_gt_dets = 0
        num_tracker_dets = 0

        for t in range(raw_data["num_timesteps"]):
            # Filter to only requested class
            gt_classes = raw_data["gt_classes"][t]
            tracker_classes = raw_data["tracker_classes"][t]

            gt_mask = gt_classes == cls_id
            tracker_mask = tracker_classes == cls_id

            data["gt_ids"][t] = raw_data["gt_ids"][t][gt_mask]
            data["gt_dets"][t] = raw_data["gt_dets"][t][gt_mask]

            data["tracker_ids"][t] = raw_data["tracker_ids"][t][tracker_mask]
            data["tracker_dets"][t] = raw_data["tracker_dets"][t][tracker_mask]
            data["tracker_confidences"][t] = raw_data["tracker_confidences"][t][tracker_mask]

            # Get similarity scores for this class
            similarity_scores = raw_data["similarity_scores"][t]
            if similarity_scores.size > 0:
                data["similarity_scores"][t] = similarity_scores[gt_mask, :][:, tracker_mask]
            else:
                data["similarity_scores"][t] = np.empty((0, 0))

            unique_gt_ids += list(np.unique(data["gt_ids"][t]))
            unique_tracker_ids += list(np.unique(data["tracker_ids"][t]))
            num_tracker_dets += len(data["tracker_ids"][t])
            num_gt_dets += len(data["gt_ids"][t])

        # Relabel IDs to be contiguous
        if len(unique_gt_ids) > 0:
            unique_gt_ids = np.unique(unique_gt_ids)
            gt_id_map = np.nan * np.ones((np.max(unique_gt_ids) + 1,))
            gt_id_map[unique_gt_ids] = np.arange(len(unique_gt_ids))
            for t in range(raw_data["num_timesteps"]):
                if len(data["gt_ids"][t]) > 0:
                    data["gt_ids"][t] = gt_id_map[data["gt_ids"][t]].astype(int)

        if len(unique_tracker_ids) > 0:
            unique_tracker_ids = np.unique(unique_tracker_ids)
            tracker_id_map = np.nan * np.ones((np.max(unique_tracker_ids) + 1,))
            tracker_id_map[unique_tracker_ids] = np.arange(len(unique_tracker_ids))
            for t in range(raw_data["num_timesteps"]):
                if len(data["tracker_ids"][t]) > 0:
                    data["tracker_ids"][t] = tracker_id_map[
                        data["tracker_ids"][t]
                    ].astype(int)

        # Record statistics
        data["num_tracker_dets"] = num_tracker_dets
        data["num_gt_dets"] = num_gt_dets
        data["num_tracker_ids"] = len(unique_tracker_ids)
        data["num_gt_ids"] = len(unique_gt_ids)
        data["num_timesteps"] = raw_data["num_timesteps"]
        data["seq"] = raw_data["seq"]

        # Verify unique IDs per timestep
        self._check_unique_ids(data, after_preproc=True)

        return data

    def _calculate_similarities(self, gt_dets_t, tracker_dets_t):
        """Calculate IoU similarity scores between gt and tracker detections.

        Uses TrackEval's box IoU implementation.

        Args:
            gt_dets_t: GT detections at timestep t (N x 4 array, xywh format)
            tracker_dets_t: Tracker detections at timestep t (M x 4 array, xywh format)

        Returns:
            IoU matrix (N x M array)
        """
        return self._calculate_box_ious(gt_dets_t, tracker_dets_t, box_format="xywh")
