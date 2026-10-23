using System.Diagnostics;
using System.Text.Json.Nodes;
using GameScripts.Survivor;

var catalog=JsonNode.Parse(File.ReadAllText(args[0]))!.AsObject();
var surface=new TerrainSurface(catalog);
var plates=catalog["terrainPlates"]!.AsArray().Select(p=>(Points:p!["outline"]!.AsArray().Select(v=>(X:(double)v![0]!,Z:(double)v[1]!)).ToArray(),Y:(double)p["top_y"]!)).ToArray();
var ramps=catalog["terrainRamps"]!.AsArray().Select(r=>{
    double x=(double)r!["low_center"]![0]!,z=(double)r["low_center"]![1]!;
    double dx=(double)r["high_center"]![0]!-x,dz=(double)r["high_center"]![1]!-z,length=Math.Sqrt(dx*dx+dz*dz);
    return (X:x,Z:z,Dx:dx/length,Dz:dz/length,Length:length,Width:(double)r["width"]!,Low:(double)r["low_y"]!,High:(double)r["high_y"]!);
}).ToArray();
// Frozen unfiltered reference: compare the optimization against the former
// full polygon/edge scan, rather than checking the new bounding boxes themselves.
double? Reference(double x,double z){
    double? height=null;
    foreach(var plate in plates){
        bool inside=false;var points=plate.Points;
        for(int i=0,j=points.Length-1;i<points.Length;j=i++){
            double dx=points[j].X-points[i].X,dz=points[j].Z-points[i].Z,length=dx*dx+dz*dz;
            double t=length>0?Math.Clamp(((x-points[i].X)*dx+(z-points[i].Z)*dz)/length,0,1):0;
            double ex=x-points[i].X-t*dx,ez=z-points[i].Z-t*dz;
            if(ex*ex+ez*ez<=1e-10){inside=true;break;}
            if((points[i].Z>z)!=(points[j].Z>z)&&x<(points[j].X-points[i].X)*(z-points[i].Z)/(points[j].Z-points[i].Z)+points[i].X)inside=!inside;
        }
        if(inside)height=height.HasValue?Math.Max(height.Value,plate.Y):plate.Y;
    }
    foreach(var r in ramps){
        double rx=x-r.X,rz=z-r.Z,along=rx*r.Dx+rz*r.Dz,lateral=Math.Abs(rx*r.Dz-rz*r.Dx);
        if(along<0||along>r.Length||lateral>r.Width*.5)continue;
        double candidate=r.Low+(r.High-r.Low)*along/r.Length;
        height=height.HasValue?Math.Max(height.Value,candidate):candidate;
    }
    return height;
}
var pointsToCheck=new List<(double X,double Z)>();
var rng=new Random(20261023);
for(int i=0;i<100000;i++)pointsToCheck.Add((rng.NextDouble()*280-140,rng.NextDouble()*280-140));
foreach(var plate in plates)for(int i=0;i<plate.Points.Length;i++){
    var a=plate.Points[i];var b=plate.Points[(i+1)%plate.Points.Length];
    foreach(double t in new[]{0,.5,1})foreach(double dx in new[]{-2e-5,-5e-6,0,5e-6,2e-5})foreach(double dz in new[]{-2e-5,-5e-6,0,5e-6,2e-5})
        pointsToCheck.Add((a.X+(b.X-a.X)*t+dx,a.Z+(b.Z-a.Z)*t+dz));
}
foreach(var r in ramps)foreach(double t in new[]{-1e-6,0,.5,1,1+1e-6})foreach(double side in new[]{-.500001,-.5,0,.5,.500001})
    pointsToCheck.Add((r.X+r.Dx*r.Length*t+r.Dz*r.Width*side,r.Z+r.Dz*r.Length*t-r.Dx*r.Width*side));
foreach(var p in pointsToCheck){
    var expected=Reference(p.X,p.Z);var actual=surface.Height(p.X,p.Z);
    if(expected!=actual)throw new Exception($"Height mismatch at {p}: {expected} != {actual}");
}
double Measure(Func<double,double,double?> query){
    var samples=new List<double>();double sum=0;
    for(int run=0;run<7;run++){
        var watch=Stopwatch.StartNew();
        foreach(var p in pointsToCheck)sum+=query(p.X,p.Z)??0;
        watch.Stop();if(run>1)samples.Add(watch.Elapsed.TotalMilliseconds);
    }
    GC.KeepAlive(sum);samples.Sort();return samples[samples.Count/2];
}
var before=Measure(Reference);var after=Measure(surface.Height);
Console.WriteLine($"unit-test PASS: {pointsToCheck.Count} real-terrain/random/edge/tolerance/ramp queries exactly match; full scan {before:F2} ms, bounded scan {after:F2} ms (desktop .NET, not phone frame time)");
