using System.Text.Json.Nodes;

namespace GameScripts.Survivor;

// Same authored plate/ramp height query as GenerateVerdantRift. No platform API.
public sealed class TerrainSurface
{
    private readonly List<(double[][] Points, double Height, double MinX, double MaxX, double MinZ, double MaxZ)> mPlates = new();
    private readonly List<(double X, double Z, double Dx, double Dz, double Length, double Width, double Low, double High)> mRamps = new();
    public TerrainSurface(JsonObject catalog)
    {
        foreach (var plate in catalog["terrainPlates"]!.AsArray())
        {
            var points=plate!["outline"]!.AsArray().Select(p=>p!.AsArray().Select(n=>n!.GetValue<double>()).ToArray()).ToArray();
            // Preserve the edge tolerance in Height, including just-outside points.
            mPlates.Add((points,plate["top_y"]!.GetValue<double>(),
                points.Length>0?points.Min(p=>p[0])-1e-5:double.PositiveInfinity,
                points.Length>0?points.Max(p=>p[0])+1e-5:double.NegativeInfinity,
                points.Length>0?points.Min(p=>p[1])-1e-5:double.PositiveInfinity,
                points.Length>0?points.Max(p=>p[1])+1e-5:double.NegativeInfinity));
        }
        foreach(var ramp in catalog["terrainRamps"]!.AsArray())
        {
            double x=ramp!["low_center"]![0]!.GetValue<double>(),z=ramp["low_center"]![1]!.GetValue<double>();
            double dx=ramp["high_center"]![0]!.GetValue<double>()-x,dz=ramp["high_center"]![1]!.GetValue<double>()-z,length=Math.Sqrt(dx*dx+dz*dz);
            mRamps.Add((x,z,dx/length,dz/length,length,ramp["width"]!.GetValue<double>(),ramp["low_y"]!.GetValue<double>(),ramp["high_y"]!.GetValue<double>()));
        }
    }
    public double? Height(double x,double z)
    {
        double? height=null;
        foreach(var plate in mPlates)
        {
            if(x<plate.MinX||x>plate.MaxX||z<plate.MinZ||z>plate.MaxZ)continue;
            bool bInside=false;var points=plate.Points;
            for(int i=0,j=points.Length-1;i<points.Length;j=i++)
            {
                double dx=points[j][0]-points[i][0],dz=points[j][1]-points[i][1],length=dx*dx+dz*dz;
                double t=length>0?Math.Clamp(((x-points[i][0])*dx+(z-points[i][1])*dz)/length,0,1):0;
                double ex=x-points[i][0]-t*dx,ez=z-points[i][1]-t*dz;
                if(ex*ex+ez*ez<=1e-10){bInside=true;break;}
                if((points[i][1]>z)!=(points[j][1]>z)&&x<(points[j][0]-points[i][0])*(z-points[i][1])/(points[j][1]-points[i][1])+points[i][0])bInside=!bInside;
            }
            if(bInside)height=height.HasValue?Math.Max(height.Value,plate.Height):plate.Height;
        }
        foreach(var ramp in mRamps)
        {
            double rx=x-ramp.X,rz=z-ramp.Z,along=rx*ramp.Dx+rz*ramp.Dz,lateral=Math.Abs(rx*ramp.Dz-rz*ramp.Dx);
            if(along<0||along>ramp.Length||lateral>ramp.Width*.5)continue;
            double candidate=ramp.Low+(ramp.High-ramp.Low)*along/ramp.Length;
            height=height.HasValue?Math.Max(height.Value,candidate):candidate;
        }
        return height;
    }
}
