import logging
from numpy import where,ones,percentile,array
from numpy.ma import getmaskarray, masked_where, median
from matplotlib.path import Path
from csv import writer,reader
from gzip import open as opengz
try:
    from itertools import izip as zip
except:
    pass
try:
    from itertools import irange as range
except:
    pass

class AggregatorMapping:
    """"Base class for aggregation of high resolution data on coarser grids.
    Based on list of lists contaning the indices in a 1D representation of the
    high resolution data for each point of the low resolution data. The actual
    definition of mappings is achieved via the subclass "Aggregator", while this
    class may be used to read already defined mappings.

    Attributes:
        indices (list of lists of integers): Mappings of high resolution grid points to coarse grid points.
        size (integer): Number of coarse grid points.
    """

    def __init__(self,indices):

        """Defines mappings of points to polygon paths.

        Args:
            indices (sequence of list of integers): Mappings of high resolution grid points to coarse grid points.
        """

        #convert mapping sequence to list
        self.indices = [idx for idx in indices] #convert mapping sequence to list
        self.size=len(self.indices)

    def __call__(self,data,method=median,fv=1.e36,progress=False):

        """Aggregates high resolution data (in 1D) on coarse resolution 1D structure.

        Args:
            data (numpy.array or numpy.ma.array in 1D): High resolution data.
            method (function): Method used for aggregating reducing a sequence of values passed as input arguments to a single value.
            fv (same array dtype as data): Fill value to be used for coarse data where no high resolution data is available.
            progress (integer): Interval in which to report mapping progress (message printing each "progress" polygons)

        Returns:
            coarse resolution data as 1D structure of same type as input data.
        """

        N=self.size
        coarseData=fv*ones(N)
        for n,idn in enumerate(self.indices):
            if progress:
                if n%progress==0: logging.info("Retrieved mappings for {} of {} polygons".format(n,N))
            if idn:
                aggregates=method(data[idn])
                coarseData[n]=where(getmaskarray(aggregates),fv,aggregates)
        if progress: lgging.info("Aggregation completed.")
        return coarseData

    def save_csv_gz(self,filename):
        """Save mapping to gzipped csv file."""
        with opengz(filename,'wt') as fid:
            csv=writer(fid)
            csv.writerows(self.indices)


class Aggregator(AggregatorMapping):

    """"Class for aggragation of high resolution data on coarser grids.
    The coarse grid needs to be defined by matplotlib.path.Path objects and
    high resolution data by an array of points. Initialisation of an Aggregator
    defines the mapping between the two grid and an object call aggregates a
    data field. Both, high and low resolution data need to be passed as 1D
    structures that are reshaped afterwards externally.

    Attributes:
        indices (list of lists of integers): Mappings of high resolution grid points to coarse grid polygons.
        size (integer): Number of coarse grid polygons.
        paths (sequence of matplotlib.path.Path objects): Polygons of coarse resolution grids.
        points (sequence of coordinate pairs): Cell centre points of high resolution grid pixels.
    """

    def __init__(self,paths,points,progress=False,geographic=False):

        """Defines mappings of points to polygon paths.

        Args:
            paths (sequence of matplotlib.path.Path objects): Polygons of coarse resolution grids.
            points (sequence of coordinate pairs): Cell centre points of high resolution grid pixels.
            progress (integer,): Interval in which to report mapping progress (message printing each "progress" polygons)
            geographic: logical flag for coordinates in geographic lon,lat coordinates. Assumes points and polygon
                vertices to be defined with longitude as first coordinate, i.e. [[lon0,lat0],[lon1,lat1],...].
                Not required if polygons and points share the same cyclic border and no polygon extends across it.
        """

        self.size=len(paths)
        apoints = array(points)
        idx=[ [] for n in range(self.size) ]
        if progress: n=0
        for path,idn in zip(paths,idx):
            if geographic:
                lon=path.vertices[:,0]
                lon_0=percentile(lon,50,interpolation='nearest')
                lon_loc=where(lon>lon_0+180,lon-360.,lon)
                lon_loc=where(lon<lon_0-180,lon+360.,lon_loc)
                path_loc=Path(array([lon_loc,path.vertices[:,1]]).T)
            else:
                path_loc=path
            if progress:
                if n%progress==0: logging.info("Retrieved mappings for {} of {} polygons".format(n,self.size))
                n+=1
            if path.get_extents().size.any():
                if geographic:
                    lon_loc=where(apoints[:,0]>lon_0+180,apoints[:,0]-360.,apoints[:,0])
                    lon_loc=where(apoints[:,0]<lon_0-180,apoints[:,0]+360.,lon_loc)
                    points_loc=array([lon_loc,apoints[:,1]]).T
                else:
                    points_loc=points
                inside=list(where(path_loc.contains_points(points_loc))[0])
                if len(inside)>0:
                    idn.extend(inside)
        self.indices = idx
        self.paths = paths
        self.points = apoints
        if progress: logging.info("Mapping completed.")


def load_csv_gz(filename):
    """Load mapping from gzipped csv file.
    Args:
        filename (str): name of csv.gz file to read

    Returns:
        AggregatorMapping instance with mapping defined in csv file."""

    with opengz(filename,'rt') as fid:
        csv=reader(fid)
        idx=[[int(n) for n in line] for line in csv]
    agg=AggregatorMapping(idx)

    return agg
