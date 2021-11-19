from typing import Dict, List, Union

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from roveranalyzer.simulators.opp.provider.hdf.HdfGroups import HdfGroups
from roveranalyzer.simulators.opp.provider.hdf.IHdfProvider import IHdfProvider
from roveranalyzer.simulators.opp.provider.hdf.Operation import Operation


class CountMapKey:
    ID = "ID"
    SIMTIME = "simtime"
    X = "x"
    Y = "y"
    COUNT = "count"
    ERR = "err"
    OWNER_DIST = "owner_dist"
    SQERR = "sqerr"


class DcdMapCount(IHdfProvider):
    def __init__(self, hdf_path):
        super().__init__(hdf_path)

    def group_key(self) -> str:
        return HdfGroups.COUNT_MAP

    def index_order(self) -> Dict:
        return {
            0: CountMapKey.SIMTIME,
            1: CountMapKey.X,
            2: CountMapKey.Y,
            3: CountMapKey.ID,
        }

    def columns(self) -> List[str]:
        return [
            CountMapKey.COUNT,
            CountMapKey.ERR,
            CountMapKey.OWNER_DIST,
            CountMapKey.SQERR,
        ]

    def default_index_key(self) -> str:
        return CountMapKey.SIMTIME

    #########################
    # Exact value functions #
    #########################
    def select_id_exact(
        self, value: int, operation: str = Operation.EQ
    ) -> pd.DataFrame:
        condition: List[str] = self._build_exact_condition(
            key=CountMapKey.ID, value=value, operation=operation
        )
        return self._select_where(condition=condition)

    def select_simtime_exact(
        self, value: int, operation: str = Operation.EQ
    ) -> pd.DataFrame:
        condition: List[str] = self._build_exact_condition(
            key=CountMapKey.SIMTIME, value=value, operation=operation
        )
        return self._select_where(condition=condition)

    def select_x_exact(
        self, value: float, operation: str = Operation.EQ
    ) -> pd.DataFrame:
        condition: List[str] = self._build_exact_condition(
            key=CountMapKey.X, value=value, operation=operation
        )
        return self._select_where(condition=condition)

    def select_y_exact(
        self, value: float, operation: str = Operation.EQ
    ) -> pd.DataFrame:
        condition: List[str] = self._build_exact_condition(
            key=CountMapKey.Y, value=value, operation=operation
        )
        return self._select_where(condition=condition)  # p[I[None,None,5,None]]

    def select_count_exact(
        self, value: float, operation: str = Operation.EQ
    ) -> pd.DataFrame:
        condition: List[str] = self._build_exact_condition(
            key=CountMapKey.COUNT, value=value, operation=operation
        )
        return self._select_where(condition=condition)

    def select_err_exact(
        self, value: float, operation: str = Operation.EQ
    ) -> pd.DataFrame:
        condition: List[str] = self._build_exact_condition(
            key=CountMapKey.ERR, value=value, operation=operation
        )
        return self._select_where(condition=condition)

    def select_owner_dist_exact(
        self, value: float, operation: str = Operation.EQ
    ) -> pd.DataFrame:
        condition: List[str] = self._build_exact_condition(
            key=CountMapKey.OWNER_DIST, value=value, operation=operation
        )
        return self._select_where(condition=condition)

    def select_sqerr_exact(
        self, value: float, operation: str = Operation.EQ
    ) -> pd.DataFrame:
        condition: List[str] = self._build_exact_condition(
            key=CountMapKey.SQERR, value=value, operation=operation
        )
        return self._select_where(condition=condition)

    def select_simtime_and_node_id_exact(
        self, simtime: int, node_id: int, operation: str = Operation.EQ
    ) -> pd.DataFrame:
        condition: List[str] = self._build_exact_condition(
            key=CountMapKey.SIMTIME, value=simtime, operation=operation
        ) + self._build_exact_condition(
            key=CountMapKey.ID, value=node_id, operation=operation
        )
        return self._select_where(condition=condition)

    #########################
    # Range value functions #
    #########################
    def select_id_range(self, _min: int, _max: int) -> pd.DataFrame:
        condition: List[str] = self._build_range_condition(
            key=CountMapKey.ID, _min=_min, _max=_max
        )
        return self._select_where(condition=condition)

    def select_simtime_range(self, _min: int, _max: int) -> pd.DataFrame:
        condition: List[str] = self._build_range_condition(
            key=CountMapKey.SIMTIME, _min=_min, _max=_max
        )
        return self._select_where(condition=condition)

    def select_x_range(self, _min: float, _max: float) -> pd.DataFrame:
        condition: List[str] = self._build_range_condition(
            key=CountMapKey.X, _min=_min, _max=_max
        )
        return self._select_where(condition=condition)

    def select_y_range(self, _min: float, _max: float) -> pd.DataFrame:
        condition: List[str] = self._build_range_condition(
            key=CountMapKey.Y, _min=_min, _max=_max
        )
        return self._select_where(condition=condition)

    def select_count_range(self, _min: float, _max: float) -> pd.DataFrame:
        condition: List[str] = self._build_range_condition(
            key=CountMapKey.COUNT, _min=_min, _max=_max
        )
        return self._select_where(condition=condition)

    def select_err_range(self, _min: float, _max: float) -> pd.DataFrame:
        condition: List[str] = self._build_range_condition(
            key=CountMapKey.ERR, _min=_min, _max=_max
        )
        return self._select_where(condition=condition)

    def select_owner_dist_range(self, _min: float, _max: float) -> pd.DataFrame:
        condition: List[str] = self._build_range_condition(
            key=CountMapKey.OWNER_DIST, _min=_min, _max=_max
        )
        return self._select_where(condition=condition)

    def select_sqerr_range(self, _min: float, _max: float) -> pd.DataFrame:
        condition: List[str] = self._build_range_condition(
            key=CountMapKey.SQERR, _min=_min, _max=_max
        )
        return self._select_where(condition=condition)

    def _to_geo(
        self, df: pd.DataFrame, to_crs: Union[str, None] = None
    ) -> gpd.GeoDataFrame:
        offset = self.get_attribute("offset")
        epsg_code = self.get_attribute("epsg")
        cell_size = self.get_attribute("cell_size")

        _index = df.index.to_frame().reset_index(drop=True)

        _index["x"] = _index["x"] - offset[0]
        _index["y"] = _index["y"] - offset[1]
        df.index = pd.MultiIndex.from_frame(_index)

        g = [
            box(x, y, x + cell_size, y + cell_size)
            for x, y in zip(_index["x"], _index["y"])
        ]
        gdf = gpd.GeoDataFrame(df, geometry=g, crs=str(epsg_code))
        if to_crs is not None:
            gdf = gdf.to_crs(epsg=to_crs.replace("EPSG:", ""))
        return gdf
