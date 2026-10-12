#pragma once

#include "Runtime/EcsFramework/Entity/ScriptableEntity.h"

namespace HEngine
{
    REFLECTION_TYPE(TouchSampleState)
    STRUCT(TouchSampleState, Fields)
    {
        REFLECTION_BODY(TouchSampleState);
        float Speed = 3.0f;
        int Score = 0;
    };

    // Explicit registration is referenced by both hosts, including optimized links.
    class TouchSample final : public ScriptableEntity
    {
    public:
        static void Register();
        static void SetTouch(float x, float y, bool bPressed);
        void LoadProperties(const Json& properties) override;
        Json SaveProperties() const override;
    protected:
        void OnCreate() override;
        void OnUpdate(Timestep ts) override;
        void OnDestroy() override;
    private:
        TouchSampleState mState;
        std::uint64_t mInputSequence = 0;
    };
}
