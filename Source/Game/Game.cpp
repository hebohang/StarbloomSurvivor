#include "GameLayer/GameLayer.h"
#include "Game/Runtime/GameBootstrap.h"

namespace HEngine
{
    Layer* CreateProjectGameLayer()
    {
        return new GameLayer();
    }
}
