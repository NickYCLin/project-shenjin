#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ShenjinSentinel.generated.h"

class UAnimSequence;
class USkeletalMeshComponent;
class UCapsuleComponent;
class USceneComponent;
class UStaticMeshComponent;

enum class ESentinelState : uint8 { Approach, Telegraph, Slam, Recover, Dead };

UCLASS()
class SHENJIN_API AShenjinSentinel : public AActor
{
    GENERATED_BODY()

public:
    AShenjinSentinel();
    virtual void Tick(float DeltaSeconds) override;
    void ReceiveStrike(float Damage);
    float GetHealthRatio() const { return Health / 1200.0f; }
    bool IsAlive() const { return State != ESentinelState::Dead; }
    bool IsPhaseTwo() const { return Health <= 600.0f; }
    FString GetStateLabel() const;

protected:
    virtual void BeginPlay() override;

private:
    void StartTelegraph();
    void Slam();
    void ResolveSlam();
    void UpdateAnimation(float DeltaSeconds, float MovementSpeed);
    float GetStrikeRadius() const { return bChargedAttack ? 570.0f : 440.0f; }

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USceneComponent> SceneRoot;
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UCapsuleComponent> Collision;
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UStaticMeshComponent> Telegraph;
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USkeletalMeshComponent> SkeletalBody;
    UPROPERTY()
    TMap<FName, TObjectPtr<UAnimSequence>> AnimationClips;

    FName CurrentAnimation;
    bool bSkeletalVisual = false;
    bool bSlamResolved = false;
    float DeathElapsed = 0.0f;
    float HitRemaining = 0.0f;
    static constexpr float SlamDuration = 0.30f;
    static constexpr float SlamImpactTime = 0.30f;

    ESentinelState State = ESentinelState::Approach;
    float Health = 1200.0f;
    float StateRemaining = 1.3f;
    float TelegraphDuration = 1.2f;
    float HitFlash = 0.0f;
    bool bChargedAttack = false;
    bool bImportedBody = false;
};
