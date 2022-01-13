import os
from functools import wraps
from itertools import combinations
from typing import Callable, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.collections import QuadMesh
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pandas import IndexSlice as Idx

import roveranalyzer.utils.plot as _Plot
from roveranalyzer.simulators.crownet.common.dcd_util import DcdMetaData
from roveranalyzer.simulators.opp.provider.hdf.DcdMapCountProvider import DcdMapCount
from roveranalyzer.simulators.opp.provider.hdf.DcdMapProvider import DcdMapProvider
from roveranalyzer.utils import logger
from roveranalyzer.utils.misc import intersect
from roveranalyzer.utils.plot import check_ax, update_dict

PlotUtil = _Plot.PlotUtil


class DcdMap:
    tsc_global_id = 0

    def __init__(
        self,
        metadata: DcdMetaData,
        position_df: pd.DataFrame,
        plotter=None,
        data_base_dir=None,
    ):
        self.metadata = metadata
        self.position_df = position_df
        self.scenario_plotter = plotter
        self.plot_wrapper = None
        self.font_dict = {
            "title": {"fontsize": 24},
            "xlabel": {"fontsize": 20},
            "ylabel": {"fontsize": 20},
            "legend": {"size": 20},
            "tick_size": 16,
        }
        self.data_base_dir = data_base_dir

    # def _load_or_create(self, pickle_name, create_f, *create_args):
    #     """
    #     Load data from hdf or create data based on :create_f:
    #     """
    #
    #     # just load data with provided create function
    #     if not self.lazy_load_from_hdf:
    #         print("create from scratch (no hdf)")
    #         return create_f(*create_args)
    #
    #     # load from hdf if exist and create if missing
    #     hdf_path = os.path.join(self.hdf_base_path, pickle_name)
    #     if os.path.exists(hdf_path):
    #         print(f"load from hdf {hdf_path}")
    #         return self.count_p.get_dataframe()
    #     else:
    #         print("create from scratch ...", end=" ")
    #         data = create_f(*create_args)
    #         print(f"write to hdf {hdf_path}")
    #         self.count_p.write_dataframe(data)
    #         return data

    def get_location(self, simtime, node_id, cell_id=False):
        try:
            ret = self.position_df.loc[simtime, node_id]
            if ret.shape == (2,):
                ret = ret.to_numpy()
                if cell_id:
                    ret = np.floor(ret / self.metadata.cell_size)
            else:
                raise TypeError()
        except (TypeError, KeyError):
            ret = np.array([-1, -1])
        return ret

    def set_scenario_plotter(self, plotter):
        self.scenario_plotter = plotter


class DcdMap2D(DcdMap):
    """
    decentralized crowed map
    """

    tsc_id_idx_name = "ID"
    tsc_time_idx_name = "simtime"
    tsc_x_idx_name = "x"
    tsc_y_idx_name = "y"

    def __init__(
        self,
        metadata: DcdMetaData,
        global_df: pd.DataFrame,
        map_df: Union[pd.DataFrame, None],
        position_df: pd.DataFrame,
        count_p: DcdMapCount = None,
        count_slice: pd.IndexSlice = None,
        map_p: DcdMapProvider = None,
        map_slice: pd.IndexSlice = None,
        plotter=None,
        **kwargs,
    ):
        super().__init__(metadata, position_df, plotter, **kwargs)
        self._map = map_df
        self._global_df = global_df
        self._count_map = None
        self._count_p = count_p
        self._count_slice = count_slice

        self._map_p = map_p
        self._map_slice = map_slice

    def iter_nodes_d2d(self, first_node_id=0):
        # index order: [time, x, y, source, node]
        _i = pd.IndexSlice

        data = self.map.loc[_i[:, :, :, :, first_node_id:], :].groupby(
            level=self.tsc_id_idx_name
        )
        for i, ts_2d in data:
            yield i, ts_2d

    @property
    def glb_map(self):
        return self._global_df

    @property
    def map(self):
        if self._map is None:
            logger.info("load map")
            self._map = self._map_p[self._map_slice, :]
            self._map = self._map.sort_index()
        return self._map

    @property
    def count_p(self):
        if self._count_p is None:
            raise ValueError("count map is not setup")
        return self._count_p

    @property
    def count_map(self):
        # lazy load data if needed
        if self._count_map is None:
            logger.info("load count map from HDF")
            self._count_map = self._count_p[self._count_slice, :]
        return self._count_map

    def all_ids(self, with_ground_truth=True):
        ids = self.position_df.index.get_level_values("node_id").unique().to_numpy()
        ids.sort()
        # ids = np.array(list(self.id_to_node.keys()))
        if with_ground_truth:
            np.insert(ids, 0, 0)
            # ids = ids[ids != 0]
        return ids

    def valid_times(self, _from=-1, _to=-1):
        time_values = self.map.index.get_level_values("simtime").unique().to_numpy()
        np.append(
            time_values,
            self.glb_map.index.get_level_values("simtime").unique().to_numpy(),
        )
        time_values = np.sort(np.unique(time_values))
        if _from >= 0:
            time_values = time_values[time_values >= _from]
        if _to >= 0:
            time_values = time_values[time_values < _to]
        return time_values

    def unique_level_values(self, level_name, df_slice=None):
        if df_slice is None:
            df_slice = ([self.tsc_global_id], [])

        idx = self.map.loc[df_slice].index.get_level_values(level_name).unique()
        return idx

    def age_mask(self, age_column, threshold):
        _mask = self.map[age_column] <= threshold
        return _mask

    def update_area(self, time_step, node_id, value_name):
        """
        create 2d matrix of density map for one instance in
        time and for one node. The returned data frame as a shape of
         (N, M) where N,M is the number of cells in X respectively Y axis
        """
        data = pd.DataFrame(
            self.count_p.select_simtime_and_node_id_exact(time_step, node_id)[
                value_name
            ]
        )
        data = data.set_index(data.index.droplevel([0, 3]))  # (x,y) as new index
        df = self.metadata.update_missing(data, real_coords=True)
        df.update(data)
        df = df.unstack().T
        return df

    def update_color_mesh(self, qmesh: QuadMesh, time_step, node_id, value_name):
        df = self.update_area(time_step, node_id, value_name)
        data = np.array(df)
        qmesh.set_array(data.ravel())
        return qmesh

    @staticmethod
    def clear_color_mesh(qmesh: QuadMesh, default_val=0):
        qmesh.set_array(qmesh.get_array() * default_val)

    def info_dict(self, x, y, time_step, node_id):
        _i = pd.IndexSlice
        _data_dict = {c: "---" for c in self.map.columns}
        _data_dict["count"] = 0
        _data_dict["source"] = -1
        _data_dict.setdefault("_node_id", -1)
        _data_dict.setdefault("_omnet_node_id", -1)
        try:
            _data = self.map.loc[_i[node_id, time_step, x, y], :]
            _data_dict = _data.to_dict()
            _data_dict["_node_id"] = int(node_id)
        except KeyError:
            pass
        finally:
            _data_dict["count"] = (
                int(_data_dict["count"]) if _data_dict["count"] != np.nan else "n/a"
            )
            try:
                _data_dict["source"] = int(_data_dict["source"])
            except ValueError:
                _data_dict["source"] = "n/a"
            for k, v in _data_dict.items():
                if type(v) == float:
                    _data_dict[k] = f"{v:.6f}"
            _data_dict.setdefault("_celll_coord", f"[{x}, {y}]")
        return _data_dict

    def own_cell(self):
        own_cell_mask = self.map["own_cell"] == 1
        places = (
            self.map[own_cell_mask]  # only own cells (cells where one node is located)
            .index.to_frame()  # make the index to the dataframe
            .reset_index(["x", "y"], drop=True)  # remove not needed index
            .drop(
                columns=["ID", "simtime"]
            )  # and remove columns created by to_frame we do not need
        )
        return places

    def create_label_positions(self, df, n=5):
        directions = 7
        teta = 2 * np.pi / directions
        r = 18.5
        rot = [
            r * np.array([np.cos(i), np.sin(i)])
            for i in np.arange(0, 2 * np.pi, step=teta, dtype=float)
        ]

        places = df.copy()
        places["x_center"] = places["x"] + 0.5 * self.metadata.cell_size
        places["y_center"] = places["y"] + 0.5 * self.metadata.cell_size
        places["x_text"] = places["x_center"]
        places["y_text"] = places["y_center"]
        for idx, row in places.iterrows():
            row["x_text"] = row["x_center"] + rot[idx[0] % directions][0]
            row["y_text"] = row["y_center"] + rot[idx[0] % directions][1]

        pairs = list(combinations(places.index.to_list(), 2))
        intersection_found = False
        for i in range(n):
            intersection_found = False
            for n1, n2 in pairs:
                # if overlapping change check overlapping
                l1 = (
                    places.loc[n1, ["x_center", "y_center", "x_text", "y_text"]]
                    .to_numpy()
                    .reshape(-1, 2)
                )
                l2 = (
                    places.loc[n2, ["x_center", "y_center", "x_text", "y_text"]]
                    .to_numpy()
                    .reshape(-1, 2)
                )
                if intersect(l1, l2):
                    _dir = int(np.floor(np.random.random() * directions))
                    places.loc[n2, "x_text"] = places.loc[n1, "x_center"] + rot[_dir][0]
                    places.loc[n2, "y_text"] = places.loc[n1, "y_center"] + rot[_dir][1]
                    print(f"intersection found {n1}<->{n2}")
                    intersection_found = True

            if not intersection_found:
                break

        if intersection_found:
            print(f"still overlaps found in annotation arrows after {n} rounds")
        return places

    def describe_raw(self, global_only=False):
        _i = pd.IndexSlice
        if global_only:
            data = self.glb_map  # only global data
            data_str = "Global"
        else:
            data = self.map
            data_str = "Local"

        desc = data.describe().T
        print("=" * 79)
        print(f"Counts with values > 0 ({data_str}):")
        print(desc.loc[["count"], ["mean", "std", "min", "max"]])
        print("-" * 79)
        print(f"Delay for each cell ({data_str}):")
        print(desc.loc[["delay"], ["mean", "std", "min", "max"]])
        print("-" * 79)
        print(f"Time since measurement was taken ({data_str}):")
        print(desc.loc[["measurement_age"], ["mean", "std", "min", "max"]])
        print("-" * 79)
        print(f"Time since last update ({data_str}):")
        print(desc.loc[["update_age"], ["mean", "std", "min", "max"]])
        print("=" * 79)

    @PlotUtil.savefigure
    @PlotUtil.plot_decorator
    def plot_summary(self, simtime, node_id, title="", **kwargs):
        kwargs.setdefault("figsize", (16, 9))
        f, ax = plt.subplots(2, 2, **kwargs)
        ax = ax.flatten()
        f.suptitle(f"Node {node_id} for time {simtime} {title}")
        self.plot_area(simtime, node_id, ax=ax[0])
        self.plot_location_map(simtime, ax=ax[1])
        self.plot_count(ax=ax[2])
        ax[3].clear()
        return f, ax

    @PlotUtil.savefigure
    @PlotUtil.with_axis
    @PlotUtil.plot_decorator
    def plot_location_map(self, time_step, *, ax: plt.Axes = None, add_legend=True):
        places = self.own_cell()
        _i = pd.IndexSlice
        places = places.loc[_i[:, time_step], :]  # select only the needed timestep

        ax.set_title(f"Node Placement at time {time_step}s")
        ax.set_aspect("equal")
        ax.set_xlim([0, self.metadata.x_dim])
        ax.set_ylim([0, self.metadata.y_dim])
        if self.scenario_plotter is not None:
            self.scenario_plotter.add_obstacles(ax)

        for _id, df in places.groupby(level=self.tsc_id_idx_name):
            # move coordinate for node :id: to center of cell.
            df = df + 0.5 * self.metadata.cell_size
            ax.scatter(df["x"], df["y"], label=f"{_id}")

        if add_legend:
            ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        return ax.get_figure(), ax

    @PlotUtil.savefigure
    @PlotUtil.with_axis
    @PlotUtil.plot_decorator
    def plot_location_map_annotated(self, time_step, *, ax: plt.Axes = None):
        places = self.own_cell()
        _i = pd.IndexSlice
        places = places.loc[_i[:, time_step], :]  # select only the needed timestep
        f, ax = self.plot_location_map(time_step, ax=ax, add_legend=False)

        # places = places.droplevel("simtime")
        places = self.create_label_positions(places)
        for _id, df in places.groupby(level=self.tsc_id_idx_name):
            # move coordinate for node :id: to center of cell.
            ax.annotate(
                text=_id,
                xy=df.loc[(_id, time_step), ["x_center", "y_center"]].to_numpy(),
                xytext=df.loc[(_id, time_step), ["x_text", "y_text"]].to_numpy(),
                xycoords="data",
                arrowprops=dict(arrowstyle="->"),
            )

        return f, ax

    def update_delay_over_distance(
        self,
        time_step,
        node_id,
        delay_kind,
        remove_null=True,
        line: Line2D = None,
        bins_width=2.5,
    ):
        df = self.map
        # remove cells with count 0
        if remove_null:
            df = self.map.loc[self.map["count"] != 0]

        # average over distance (ignore node_id)
        if bins_width > 0:
            df = df.loc[Idx[:, time_step], ["owner_dist", delay_kind]]
            bins = int(np.floor(df["owner_dist"].max() / bins_width))
            df = df.groupby(pd.cut(df["owner_dist"], bins)).mean().dropna()
            df.index = df.index.rename("dist_bin")
        else:
            df = df.loc[Idx[node_id, time_step], ["owner_dist", delay_kind]]

        df = df.sort_values(axis=0, by=["owner_dist"])
        if line is not None:
            line.set_ydata(df[delay_kind].to_numpy())
            line.set_xdata(df["owner_dist"].to_numpy())
        return df

    def apply_ax_props(self, ax: plt.Axes, ax_prop: dict):
        for k, v in ax_prop.items():
            getattr(ax, f"set_{k}", None)(v, **self.font_dict[k])

    def update_cell_error(
        self,
        time_slice: slice,
        value: str = "err",
        agg_func: Union[Callable, str, list, dict] = "mean",
        drop_index: bool = False,
        name: Union[str, None] = None,
        *args,
        **kwargs,
    ) -> pd.DataFrame():
        """
        Aggregated cell error over all nodes over a given time.
        """
        # select time slice. Do not select ground truth (ID = 0)
        df = self.count_p[pd.IndexSlice[time_slice, :, :, 1:], value]
        df = df.groupby(by=["x", "y"]).aggregate(func=agg_func, *args, **kwargs)
        if name is not None:
            df = df.rename(columns={value: name})
        if drop_index:
            df = df.reset_index(drop=True)
        return df

    def update_error_over_distance(
        self,
        time_step,
        node_id,
        value,
        line: Line2D = None,
        bins_width=2.5,
    ):
        df = self.count_p.select_simtime_and_node_id_exact(time_step, node_id)[
            ["owner_dist", value]
        ]
        df = df.reset_index(drop=True)

        # average over distance (ignore node_id)
        if bins_width > 0:
            bins = int(np.floor(df["owner_dist"].max() / bins_width))
            df = df.groupby(pd.cut(df["owner_dist"], bins)).mean().dropna()
            df.index = df.index.rename("dist_bin")

        df = df.sort_values(axis=0, by=["owner_dist"])
        if line is not None:
            line.set_ydata(df[value].to_numpy())
            line.set_xdata(df["owner_dist"].to_numpy())
        return df

    @PlotUtil.savefigure
    @PlotUtil.with_axis
    @PlotUtil.plot_decorator
    def plot_error_histogram(
        self,
        time_slice: slice = slice(None),
        value="err",
        agg_func="mean",
        *,
        stat: str = "count",  # "percent"
        fill: bool = True,
        ax: plt.Axes = None,
        **hist_kwargs,
    ):
        if time_slice == slice(None):
            _ts = self.count_p.get_time_interval()
            time_slice = slice(_ts[0], _ts[1])
        _t = f"Cell count Error ('{value}') for Time {time_slice.start}"
        if time_slice.stop is not None:
            _t += f" - {time_slice.stop}"
        ax.set_title(_t)
        ax.set_xlabel(f"{value}")

        data = self.update_cell_error(time_slice, value, agg_func, drop_index=True)
        ax = sns.histplot(data=data, stat=stat, fill=fill, ax=ax, **hist_kwargs)
        return ax.get_figure(), ax

    @PlotUtil.savefigure
    @PlotUtil.with_axis
    @PlotUtil.plot_decorator
    def plot_error_quantil_histogram(
        self,
        value="err",
        agg_func="mean",
        *,
        stat: str = "count",  # "percent"
        fill: bool = False,
        ax: plt.Axes = None,
        **hist_kwargs,
    ):
        tmin, tmax = self.count_p.get_time_interval()
        time = (tmax - tmin) / 4
        intervals = {
            f"Time Quantil {i+1}": slice(time * i, time * i + time) for i in range(4)
        }

        ax.set_title("Cell Error Histogram")
        ax.set_xlabel(value)

        data = self.update_cell_error(
            slice(None), value, agg_func, name="All", drop_index=True
        )
        quant = [
            self.update_cell_error(v, value, agg_func, name=k, drop_index=True)
            for k, v in intervals.items()
        ]
        data = pd.concat([data, *quant], axis=1)

        sns.histplot(
            data=data,
            stat=stat,
            common_norm=False,
            fill=fill,
            legend=True,
            **hist_kwargs,
        )
        return ax.get_figure(), ax

    @PlotUtil.savefigure
    @PlotUtil.plot_decorator
    def plot_error_over_distance(
        self,
        time_step,
        node_id,
        value,
        label=None,
        *,
        ax=None,
        fig_dict: dict = None,
        ax_prop: dict = None,
        **kwargs,
    ):

        f, ax = check_ax(ax, **fig_dict if fig_dict is not None else {})
        df = self.update_error_over_distance(
            time_step, node_id, value, line=None, **kwargs
        )

        if label is None:
            label = value
        ax.plot("owner_dist", value, data=df, label=label)

        ax_prop = {} if ax_prop is None else ax_prop
        ax_prop.setdefault(
            "title",
            f"Error({value}) over Distance",
        )
        ax_prop.setdefault("xlabel", "Cell distance (euklid) to owners location [m]")
        ax_prop.setdefault("ylabel", f"{value}")

        ax.lines[0].set_linestyle("None")
        ax.lines[0].set_marker("o")

        self.apply_ax_props(ax, ax_prop)

        return f, ax

    @PlotUtil.savefigure
    @PlotUtil.plot_decorator
    def plot_delay_over_distance(
        self,
        time_step,
        node_id,
        value,
        remove_null=True,
        label=None,
        *,
        ax: plt.Axes = None,
        fig_dict: dict = None,
        ax_prop: dict = None,
        **kwargs,
    ):
        """
        Plot delay_kind* over the distance between measurements location (cell) and
        the position of the map owner.

        Default data view: per node / per time / all cells

        *)delay_kind: change definition of delay using the delay_kind parameter.
          one of: ["delay", "measurement_age", "update_age"]
        """

        f, ax = check_ax(ax, **fig_dict if fig_dict is not None else {})
        df = self.update_delay_over_distance(
            time_step, node_id, value, remove_null=remove_null, line=None, **kwargs
        )

        if label is None:
            label = value
        ax.plot("owner_dist", value, data=df, label=label)

        ax_prop = {} if ax_prop is None else ax_prop
        ax_prop.setdefault(
            "title",
            f"Delay({value}) over Distance",
        )
        ax_prop.setdefault("xlabel", "Cell distance (euklid) to owners location [m]")
        ax_prop.setdefault("ylabel", "Delay in [s]")

        ax.lines[0].set_linestyle("None")
        ax.lines[0].set_marker("o")

        self.apply_ax_props(ax, ax_prop)

        return f, ax

    @PlotUtil.savefigure
    @PlotUtil.plot_decorator
    def plot_area(
        self,
        time_step: float,
        node_id: int,
        value: str,
        *,
        ax=None,
        pcolormesh_dict: dict = None,
        fig_dict: dict = None,
        ax_prop: dict = None,
        **kwargs,
    ) -> Tuple[Figure, Axes]:
        """
        Birds eyes view of density in a 2D color mesh with X/Y spanning the
        area under observation. Z axis (density) is shown with given color grading.

        Default data view: per node / per time / all cells
        """
        df = self.update_area(time_step, node_id, value)
        f, ax = check_ax(ax, **fig_dict if fig_dict is not None else {})

        cell = self.get_location(time_step, node_id, cell_id=False)
        if "title" in kwargs:
            ax.set_title(kwargs["title"], **self.font_dict["title"])
        else:
            ax.set_title(
                f"Area plot of '{value}'. node: {node_id} time: "
                f"{time_step} cell [{cell[0]}, {cell[1]}]",
                **self.font_dict["title"],
            )
        ax.set_aspect("equal")
        ax.tick_params(axis="x", labelsize=self.font_dict["tick_size"])
        ax.tick_params(axis="y", labelsize=self.font_dict["tick_size"])

        # if self.scenario_plotter is not None:
        #     self.scenario_plotter.add_obstacles(ax)

        _d = update_dict(pcolormesh_dict, shading="flat")

        pcm = ax.pcolormesh(self.metadata.X_flat, self.metadata.Y_flat, df, **_d)

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        cax.set_label("colorbar")
        cax.tick_params(axis="y", labelsize=self.font_dict["tick_size"])
        f.colorbar(pcm, cax=cax)

        ax.update(ax_prop if ax_prop is not None else {})

        return f, ax

    @PlotUtil.savefigure
    @PlotUtil.plot_decorator
    def plot_count(self, *, ax=None, **kwargs) -> Tuple[Figure, Axes]:
        f, ax = check_ax(ax, **kwargs)
        ax.set_title("Total node count over time", **self.font_dict["title"])
        ax.set_xlabel("time [s]", **self.font_dict["xlabel"])
        ax.set_ylabel("total node count", **self.font_dict["ylabel"])

        for _id, df in self.iter_nodes_d2d(first_node_id=1):
            df_time = df.groupby(level=self.tsc_time_idx_name).sum()
            ax.plot(df_time.index, df_time["count"], label=f"{_id}")

        g = self.glb_map.groupby(level=self.tsc_time_idx_name).sum()
        ax.plot(
            g.index.get_level_values(self.tsc_time_idx_name),
            g["count"],
            label=f"0",
        )
        ax.legend()
        return f, ax

    @PlotUtil.savefigure
    @PlotUtil.plot_decorator
    def plot_count_diff(self, *, ax=None, **kwargs) -> Tuple[Figure, Axes]:
        f, ax = check_ax(ax, **kwargs)
        ax.set_title("Node Count over Time", **self.font_dict["title"])
        ax.set_xlabel("Time [s]", **self.font_dict["xlabel"])
        ax.set_ylabel("Pedestrian Count", **self.font_dict["ylabel"])
        _i = pd.IndexSlice
        nodes = (
            self.map.loc[_i[:], _i["count"]]
            .groupby(level=[self.tsc_id_idx_name, self.tsc_time_idx_name])
            .sum()
            .groupby(level="simtime")
            .mean()
        )
        nodes_std = (
            self.map.loc[_i[:], _i["count"]]
            .groupby(level=[self.tsc_id_idx_name, self.tsc_time_idx_name])
            .sum()
            .groupby(level="simtime")
            .std()
        )
        glb = self.glb_map.groupby(level=self.tsc_time_idx_name).sum()["count"]
        ax.plot(nodes.index, nodes, label="Mean count")
        ax.fill_between(
            nodes.index,
            nodes + nodes_std,
            nodes - nodes_std,
            alpha=0.35,
            interpolate=True,
            label="Count +/- 1 std",
        )
        ax.plot(glb.index, glb, label="Actual count")
        f.legend()
        return f, ax


class DcdMap2DMulti(DcdMap2D):
    tsc_source_idx_name = "source"

    def __init__(
        self,
        metadata: DcdMetaData,
        global_df: pd.DataFrame,
        map_df: pd.DataFrame,
        position_df: pd.DataFrame,
        map_all_df: pd.DataFrame,
        **kwargs,
    ):
        """
        Parameters
        ----------
        metadata: Meta data instance for current map. cell size, map size
        node_id_map: Mapping between node
        """
        super().__init__(metadata, global_df, map_df, position_df, **kwargs)
        self.map_all_df = map_all_df

    def info_dict(self, x, y, time_step, node_id):
        info_dict = super().info_dict(x, y, time_step, node_id)
        try:
            others = self.map_all_df.loc[
                pd.IndexSlice[node_id, time_step, x, y, :],
                ["count", "measured_t", "received_t"],
            ]
            _data = []
            for index, row in others.iterrows():
                row_dict: dict = row.to_dict()
                row_dict.setdefault("_node_id", index[4])
                _data.append(row_dict)

            info_dict.setdefault("y_other_values_#", len(_data))
            info_dict.setdefault("y_other_mean_count", others.mean().loc["count"])
            info_dict.setdefault("z_other_values", _data)
        except KeyError:
            pass

        return info_dict
