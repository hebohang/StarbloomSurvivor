#pragma once

#include "Game/Runtime/RuntimeGameLayer.h"

namespace HEngine
{
    class GameLayer final : public RuntimeGameLayer
    {
    public:
        void OnAttach() override;
    };
}
