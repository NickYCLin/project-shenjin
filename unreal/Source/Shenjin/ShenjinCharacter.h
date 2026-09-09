#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "ShenjinCharacter.generated.h"

class UCameraComponent;
class USpringArmComponent;
class USceneComponent;
class UStaticMeshComponent;

UENUM(BlueprintType)
enum class EShenjinOath : uint8
{
    Ember,
    Aegis,
    Gale
};

UCLASS()
class SHENJIN_API AShenjinCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    AShenjinCharacter();
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    void ReceiveStrike(float Damage);
    float GetHealthRatio() const { return Health / 100.0f; }
    float GetDivineCharge() const { return DivineCharge; }
    float GetDivineSeconds() const { return DivineRemaining; }
    float GetDodgeCooldown() const { return DodgeCooldown; }
    bool IsAlive() const { return Health > 0.0f; }
    bool IsInvulnerable() const { return DodgeRemaining > 0.0f; }
    EShenjinOath GetOath() const { return Oath; }
    FString GetOathLabel() const;

protected:
    virtual void BeginPlay() override;

private:
    void MoveForward(float Value);
    void MoveRight(float Value);
    void Turn(float Value);
    void LookUp(float Value);
    void Attack();
    void ResolveAttack();
    void Dodge();
    void ActivateDivineForm();
    void SwitchOath();
    void Restart();
    bool CanAct() const;
    void UpdateOathVisual();

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UCameraComponent> FollowCamera;
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USceneComponent> WeaponPivot;
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UStaticMeshComponent> Spear;
    UPROPERTY()
    TArray<TObjectPtr<UStaticMeshComponent>> DivineArms;

    EShenjinOath Oath = EShenjinOath::Ember;
    float Health = 100.0f;
    float DivineCharge = 40.0f;
    float DivineRemaining = 0.0f;
    float DodgeRemaining = 0.0f;
    float DodgeCooldown = 0.0f;
    float OathCooldown = 0.0f;
    float AttackRemaining = 0.0f;
    float AttackDuration = 0.5f;
    float HitFlash = 0.0f;
    bool bAttackResolved = false;
    FVector DodgeDirection = FVector::ForwardVector;
};
