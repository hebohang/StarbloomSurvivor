namespace GameScripts.Survivor;

// Reused broad-phase buckets. Queries are conservative; gameplay still checks
// exact distances and can restore spawn order before applying damage/RNG.
public sealed class SpatialGrid<T>
{
    private readonly double mCellSize;
    // Integral keys avoid randomized composite hashing/host entropy on WX.
    private readonly Dictionary<long,List<T>> mCells=new();
    private readonly Stack<List<T>> mPool=new();
    public SpatialGrid(double cellSize=4){if(!(cellSize>0)||!double.IsFinite(cellSize))throw new ArgumentOutOfRangeException(nameof(cellSize));mCellSize=cellSize;}
    private int Cell(double value)=>(int)Math.Floor(value/mCellSize);
    private static long Key(int x,int z)=>((long)x<<32)|(uint)z;
    public void Clear(){foreach(var cell in mCells.Values){cell.Clear();mPool.Push(cell);}mCells.Clear();}
    public void Add(T item,double x,double z){long key=Key(Cell(x),Cell(z));if(!mCells.TryGetValue(key,out var cell))mCells[key]=cell=mPool.Count>0?mPool.Pop():new(8);cell.Add(item);}
    public void Query(double x,double z,double radius,List<T> result,int limit=int.MaxValue,int offset=0)
    {
        result.Clear();int minX=Cell(x-radius),maxX=Cell(x+radius),minZ=Cell(z-radius),maxZ=Cell(z+radius);
        if((long)(maxX-minX+1)*(maxZ-minZ+1)>mCells.Count*4L){
            foreach(var pair in mCells){int cx=(int)(pair.Key>>32),cz=(int)pair.Key;if(cx<minX||cx>maxX||cz<minZ||cz>maxZ)continue;Append(pair.Value,result,limit,offset);if(result.Count>=limit)return;}
        }else for(int iz=minZ;iz<=maxZ;iz++)for(int ix=minX;ix<=maxX;ix++){
            if(mCells.TryGetValue(Key(ix,iz),out var cell))Append(cell,result,limit,offset);if(result.Count>=limit)return;
        }
    }
    private static void Append(List<T> cell,List<T> result,int limit,int offset){int start=(int)((uint)offset%(uint)cell.Count);for(int i=0;i<cell.Count&&result.Count<limit;i++)result.Add(cell[(start+i)%cell.Count]);}
}
