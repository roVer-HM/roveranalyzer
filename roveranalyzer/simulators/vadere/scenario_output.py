import glob
import hashlib
import json
import os
from os.path import isdir, isfile, join

from roveranalyzer.utils.dataframe import LazyDataFrame
from roveranalyzer.utils.file import clean_dir_name, read_json_to_dict
from roveranalyzer.utils.path import JsonPath


class NamedFiles:
    def __init__(self):
        pass


class ScenarioOutput:
    """
    attributes:
    output_dir:         path to output directory (may be relative or absolute
    output_dir_name:    name of output directory
    scenario_path:      path to scenario file within output directory
    scenario:           dict representing the whole scenario file
    scenario_hash:      hash of scenario file based on string.strip(' \s\r\n') to ensure cross platform comparison
    trajectories_hash:  hash of trajectory file base ond string.strip(' \s\r\n') to ensure cross platform comparison
    file:               dict containing LazyDataFrameWrapper objects to create DataFrames for each output file.
                        The Key is the file name with '.' and '-' replaced with '_'.
    named_files:        dummpy object containing attributes for each file in *file* with '.' and '-' replaced with '_'
                        These attributes are also LazyDataFrameWrapper
    """

    TRAJECTORY_FILE = ["postvis.traj", "postvis.trajectories"]

    def __init__(
        self, scenario_file_path: str, output_dir: str, expect_all_outputs: bool
    ):

        assert isfile(scenario_file_path), "Filepath to .scenario does not exist"
        assert isdir(output_dir), "Filepath containing processor outputs does not exist"

        self.output_dir = output_dir
        self.output_dir_name = os.path.basename(output_dir)
        self.scenario_path = scenario_file_path
        self.scenario = read_json_to_dict(self.scenario_path)
        self.scenario_hash = self._get_md5_sum(self.scenario_path)
        traj_path = self.get_trajectory_file(self.output_dir, raise_on_err=False)
        if traj_path is not None:
            self.trajectories_hash = self._get_md5_sum(traj_path)
        else:
            if expect_all_outputs:
                raise FileNotFoundError(
                    f"no trajectory files [{', '.join(self.TRAJECTORY_FILE)}]"
                    f" found in {self.scenario_path}."
                )
            else:
                self.trajectories_hash = -1

        # add attributes for output files programmatically to the ScenarioOutput object. These attributes
        # are recognized by the code completion tool of jupyter-notebook and allow easy access to the each
        # output file in one simulation run.
        self.files = dict()
        self.named_files = NamedFiles()

        for file in self.scenario["processWriters"]["files"]:
            f_name = file["filename"]
            f_path = join(self.output_dir, f_name)
            if os.path.exists(f_path):
                attr_df = clean_dir_name(f_name)
                setattr(
                    self.named_files, "df_" + attr_df, LazyDataFrame.from_path(f_path)
                )
                self.files[f_name] = LazyDataFrame.from_path(f_path)

                attr_info = "info_{}".format(attr_df)
                attr_info_dict = dict()
                attr_info_dict["keyType"] = file["type"].split(".")[-1]
                attr_info_dict["dataprocessors"] = self._get_used_processors_(
                    file["processors"]
                )
                attr_info_dict["path"] = os.path.abspath(f_path)
                setattr(self.named_files, attr_info, attr_info_dict)
            else:
                if expect_all_outputs:
                    raise FileNotFoundError(f"File <<{file}>> not found in")

    @classmethod
    def get_trajectory_file(cls, base_path, raise_on_err=True):
        """
        return first match.
        """
        for file_name in cls.TRAJECTORY_FILE:
            traj_path = os.path.join(base_path, file_name)
            if os.path.exists(traj_path):
                return traj_path
        if raise_on_err:
            raise FileNotFoundError(
                f"no trajectory files [{', '.join(cls.TRAJECTORY_FILE)}] found in {base_path}."
            )
        else:
            return None

    @classmethod
    def create_output_from_project_output(
        cls, output_dir: str, expect_all_outputs: bool = True
    ):
        if not os.path.isdir(output_dir):
            raise FileNotFoundError(
                "Directory at {} does not exist.".format(output_dir)
            )

        scenario_files = glob.glob(os.path.join(output_dir, "*.scenario"))
        if not len(scenario_files) == 1:
            raise FileNotFoundError(
                "Output directory has none or to many scenario file(s)"
            )

        return cls(scenario_files[0], output_dir, expect_all_outputs)

    @classmethod
    def create_output_from_suqc_output(
        cls, base_path, run_id=None, expect_all_outputs: bool = False
    ):
        """
        Load ScenarioOutput from suqc output. If run_id is not given the base_path is treated as
        the output directory
        :param base_path:           base path to suqc output directory and scenario file or output
        :param run_id:              id of the run
        :param expect_all_outputs:  if true all output files from the scenario file must be present.
        :return:                    ScenarioOutput object
        """
        if run_id is not None:
            output_dir = join(base_path, "".join([str(run_id).zfill(10), "_output"]))
            if not isdir(output_dir):
                raise FileNotFoundError(
                    "Directory at {} does not exist.".format(output_dir)
                )

            scenario_file_path = join(
                base_path, "".join([str(run_id).zfill(10), ".scenario"])
            )
            if not isfile(scenario_file_path):
                raise FileNotFoundError(
                    "Output directory has none or to many scenario file(s)"
                )
        else:
            output_dir = base_path
            if not isdir(output_dir):
                raise FileNotFoundError(
                    "Directory at {} does not exist.".format(output_dir)
                )

            scenario_file_path = f"{base_path[:-7]}.scenario"
            if not isfile(scenario_file_path):
                raise FileNotFoundError(
                    "Output directory has none or to many scenario file(s)"
                )

        return cls(scenario_file_path, output_dir, expect_all_outputs)

    def _get_used_processors_(self, ids):
        """
        :param ids: list of processor ids used in one output file
        :return:    the names of DataProcessors corresponding to the given ids. Only the last component of the
                    dataProcessor name is returned
        """
        processor_list = [
            p for p in self.scenario["processWriters"]["processors"] if p["id"] in ids
        ]
        return [p["type"].split(".")[-1] for p in processor_list]

    def path(self, path):
        return JsonPath(path).get(self.scenario)

    def info(self, short=True):
        """
        :return: print important scenario settings based on scenario file from the output directory
        """
        if short:
            print("output-dir:", self.output_dir)
            print("name:", self.scenario["name"])
            print("mainModel:", self.scenario["scenario"]["mainModel"])
        else:
            print("mainModel:", self.scenario["scenario"]["mainModel"])
            print("attributesSimulation:")
            print(
                json.dumps(self.scenario["scenario"]["attributesSimulation"], indent=2)
            )
            print("attributesModel:")
            print(json.dumps(self.scenario["scenario"]["attributesModel"], indent=2))

    def get_scenario_name(self):
        try:
            name = self.scenario["name"]
        except KeyError as err:
            raise KeyError(
                "The scenario file in output {} is corrupt. Scenario file not found. Err:{}".format(
                    self.output_dir_name, err
                )
            )

        return name

    def get_bound_offset(self):
        try:
            offset = [
                self.scenario["scenario"]["topography"]["attributes"]["bounds"]["x"],
                self.scenario["scenario"]["topography"]["attributes"]["bounds"]["y"],
            ]
        except KeyError as err:
            raise KeyError(
                "The scenario file in output {} is corrupt. topograhpy bound not found. Err:{}".format(
                    self.output_dir_name, err
                )
            )

        return offset

    @staticmethod
    def _get_md5_sum(path):

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
            text = text.strip(" \t\n\r")
            hash_md5 = hashlib.md5(text.encode("utf-8"))
        return hash_md5.hexdigest()
