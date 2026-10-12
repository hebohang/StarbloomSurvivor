#include "GameLayer.h"
#include "TouchSample.h"

namespace HEngine
{
    void GameLayer::OnAttach()
    {
        TouchSample::Register();
        RuntimeGameLayer::OnAttach();
    }
}
