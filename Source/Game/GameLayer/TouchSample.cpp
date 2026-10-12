#include "TouchSample.h"
#include "Runtime/EcsFramework/Component/Script/NativeScriptComponent.h"
#include "Runtime/EcsFramework/Component/Transform/TransformComponent.h"
#include "Runtime/EcsFramework/Component/Shape/SpriteRendererComponent.h"
#include "Runtime/Core/Meta/Serializer/Serializer.h"
#include "Runtime/Core/Log/Log.h"
#include "_generated/serializer/TouchSample.gen.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace HEngine
{
    namespace { glm::vec2 sTouch{}; bool sPressed = false; std::uint64_t sInputSequence = 0; }
    void TouchSample::Register()
    {
        NativeScriptComponent::RegisterType("TouchSample", [](NativeScriptComponent& component) { component.Bind<TouchSample>(); });
    }
    void TouchSample::SetTouch(float x, float y, bool bPressed)
    {
        sTouch = { x, y };
        if (bPressed && !sPressed) ++sInputSequence;
        sPressed = bPressed;
    }
    void TouchSample::LoadProperties(const Json& properties)
    {
        Serializer::Deserialize(properties, mState);
        if (!std::isfinite(mState.Speed) || mState.Speed < 0 || mState.Speed > 20 || mState.Score < 0 || mState.Score > 1000000)
            throw std::runtime_error("TouchSample properties are out of range.");
    }
    Json TouchSample::SaveProperties() const
    {
        Json result;
        Serializer::Serialize(result, mState);
        return result;
    }
    void TouchSample::OnCreate()
    {
        mInputSequence = sInputSequence;
        HE_CORE_INFO("[NativeScript] TouchSample created speed={0} score={1}", mState.Speed, mState.Score);
    }
    void TouchSample::OnDestroy() { mInputSequence = sInputSequence; }
    void TouchSample::OnUpdate(Timestep ts)
    {
        // Preserve a tap that begins and ends between two simulation frames.
        mState.Score += static_cast<int>(std::min<std::uint64_t>(sInputSequence - mInputSequence, 1000000 - mState.Score));
        mInputSequence = sInputSequence;
        auto& transform = GetComponent<TransformComponent>();
        if (sPressed)
        {
            const glm::vec2 delta = sTouch - glm::vec2(transform.Translation);
            const float distance = glm::length(delta);
            const float step = mState.Speed * std::clamp(ts.GetSeconds(), 0.0f, 0.05f);
            if (distance > 0.00001f) transform.Translation += glm::vec3(delta * (std::min(step, distance) / distance), 0);
        }
        GetComponent<SpriteRendererComponent>().Color = mState.Score % 2 ? glm::vec4(1, 0.45f, 0.3f, 0.7f) : glm::vec4(0.3f, 0.8f, 1, 0.7f);
    }
}
