namespace GameScripts.Survivor;

public sealed partial class WebGameSession
{
    private long mNextVisualId, mNextPresentationEvent;
    private bool bPresentationEvents;
    private readonly Queue<PresentationEvent> mPresentationEvents = new();
    private sealed record PresentationEvent(long Sequence, string Kind, string Weapon, double X, double Y, double Z, double Damage, bool Critical, double Dx, double Dz);
    public void EnablePresentationEvents() => bPresentationEvents = true;
    private void EmitPresentation(string kind, string weapon, double x, double z, double damage = 0, bool critical = false, double dx = 0, double dz = 1)
    {
        if (!bPresentationEvents) return;
        mPresentationEvents.Enqueue(new(++mNextPresentationEvent,kind,weapon,x,mTerrain.Height(x,z)??0,z,damage,critical,dx,dz));
        while(mPresentationEvents.Count>64)mPresentationEvents.Dequeue();
    }
}
