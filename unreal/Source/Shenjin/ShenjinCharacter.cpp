#include "ShenjinCharacter.h"

#include "ShenjinGameMode.h"
#include "ShenjinSentinel.h"
#include "ShenjinVisuals.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/GameplayStatics.h"

AShenjinCharacter::AShenjinCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    GetCapsuleComponent()->InitCapsuleSize(38.0f, 92.0f);
    bUseControllerRotationYaw = false;
    bUseControllerRotationPitch = false;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0.0f, 720.0f, 0.0f);
    GetCharacterMovement()->MaxWalkSpeed = 560.0f;
    GetCharacterMovement()->BrakingDecelerationWalking = 2200.0f;

    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->TargetArmLength = 600.0f;
    CameraBoom->SocketOffset = FVector(0.0f, 45.0f, 80.0f);
    CameraBoom->bUsePawnControlRotation = true;
    CameraBoom->bEnableCameraLag = true;
    CameraBoom->CameraLagSpeed = 12.0f;
    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
    FollowCamera->FieldOfView = 82.0f;

    Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("HeroVisual"));
    Body->SetupAttachment(RootComponent);
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    WeaponPivot = CreateDefaultSubobject<USceneComponent>(TEXT("WeaponPivot"));
    WeaponPivot->SetupAttachment(RootComponent);
    Spear = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Spear"));
    Spear->SetupAttachment(WeaponPivot);
    Spear->SetCollisionEnabled(ECollisionEnabled::NoCollision);

    for (int32 Index = 0; Index < 6; ++Index)
    {
        UStaticMeshComponent* Arm = CreateDefaultSubobject<UStaticMeshComponent>(
            *FString::Printf(TEXT("DivineArm%d"), Index));
        Arm->SetupAttachment(RootComponent);
        Arm->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Arm->SetCastShadow(false);
        DivineArms.Add(Arm);
    }
}

void AShenjinCharacter::BeginPlay()
{
    Super::BeginPlay();
    if (UStaticMesh* HeroMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Shenjin/Meshes/hero.hero")))
    {
        Body->SetStaticMesh(HeroMesh);
        Body->SetRelativeLocation(FVector(0.0f, 0.0f, -92.0f));
        // Blender models face -Y; UE characters move along local +X.
        Body->SetRelativeRotation(FRotator(0.0f, 90.0f, 0.0f));
    }
    else
    {
        Body->SetStaticMesh(ShenjinVisuals::Shape(TEXT("Cube")));
        Body->SetRelativeScale3D(FVector(0.65f, 0.5f, 1.84f));
        ShenjinVisuals::Tint(Body, FLinearColor(0.1f, 0.25f, 0.3f));
    }

    if (UStaticMesh* WeaponMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Shenjin/Meshes/spear.spear")))
    {
        Spear->SetStaticMesh(WeaponMesh);
    }
    else
    {
        Spear->SetStaticMesh(ShenjinVisuals::Shape(TEXT("Cylinder")));
        Spear->SetRelativeScale3D(FVector(0.055f, 0.055f, 2.4f));
        // Engine cylinders pivot at their center; FBX spear pivots at its base.
        Spear->SetRelativeLocation(FVector(0.0f, 0.0f, 120.0f));
        ShenjinVisuals::Tint(Spear, FLinearColor(0.8f, 0.5f, 0.1f));
    }
    WeaponPivot->SetRelativeLocation(FVector(25.0f, 42.0f, -55.0f));
    WeaponPivot->SetRelativeRotation(FRotator(-20.0f, 0.0f, 0.0f));
    for (int32 Index = 0; Index < DivineArms.Num(); ++Index)
    {
        UStaticMeshComponent* Arm = DivineArms[Index];
        Arm->SetStaticMesh(ShenjinVisuals::Shape(TEXT("Cube")));
        const float Side = Index % 2 == 0 ? -1.0f : 1.0f;
        const int32 Row = Index / 2;
        Arm->SetRelativeLocation(FVector(-28.0f, Side * (75.0f + Row * 18.0f), 15.0f + Row * 34.0f));
        Arm->SetRelativeScale3D(FVector(0.16f, 1.05f, 0.15f));
        Arm->SetRelativeRotation(FRotator(0.0f, Side * -20.0f, Side * (25.0f + Row * 20.0f)));
        Arm->SetVisibility(false);
    }
    UpdateOathVisual();
    if (APlayerController* PC = Cast<APlayerController>(Controller))
    {
        PC->SetControlRotation(FRotator(-14.0f, 90.0f, 0.0f));
        PC->SetInputMode(FInputModeGameOnly());
        PC->bShowMouseCursor = false;
    }
}

bool AShenjinCharacter::CanAct() const
{
    const AShenjinGameMode* Mode = Cast<AShenjinGameMode>(UGameplayStatics::GetGameMode(this));
    return IsAlive() && Mode && !Mode->IsEncounterOver();
}

void AShenjinCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindAxis(TEXT("MoveForward"), this, &AShenjinCharacter::MoveForward);
    Input->BindAxis(TEXT("MoveRight"), this, &AShenjinCharacter::MoveRight);
    Input->BindAxis(TEXT("Turn"), this, &AShenjinCharacter::Turn);
    Input->BindAxis(TEXT("LookUp"), this, &AShenjinCharacter::LookUp);
    Input->BindAction(TEXT("Attack"), IE_Pressed, this, &AShenjinCharacter::Attack);
    Input->BindAction(TEXT("Dodge"), IE_Pressed, this, &AShenjinCharacter::Dodge);
    Input->BindAction(TEXT("DivineForm"), IE_Pressed, this, &AShenjinCharacter::ActivateDivineForm);
    Input->BindAction(TEXT("SwitchOath"), IE_Pressed, this, &AShenjinCharacter::SwitchOath);
    Input->BindAction(TEXT("Restart"), IE_Pressed, this, &AShenjinCharacter::Restart);
}

void AShenjinCharacter::MoveForward(float Value)
{
    if (CanAct() && Controller && DodgeRemaining <= 0.0f)
    {
        const FRotator Heading(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
        AddMovementInput(FRotationMatrix(Heading).GetUnitAxis(EAxis::X), Value);
    }
}

void AShenjinCharacter::MoveRight(float Value)
{
    if (CanAct() && Controller && DodgeRemaining <= 0.0f)
    {
        const FRotator Heading(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
        AddMovementInput(FRotationMatrix(Heading).GetUnitAxis(EAxis::Y), Value);
    }
}

void AShenjinCharacter::Turn(float Value) { AddControllerYawInput(Value); }
void AShenjinCharacter::LookUp(float Value) { AddControllerPitchInput(Value); }

void AShenjinCharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    DodgeCooldown = FMath::Max(0.0f, DodgeCooldown - DeltaSeconds);
    OathCooldown = FMath::Max(0.0f, OathCooldown - DeltaSeconds);
    DivineRemaining = FMath::Max(0.0f, DivineRemaining - DeltaSeconds);
    HitFlash = FMath::Max(0.0f, HitFlash - DeltaSeconds);

    if (DodgeRemaining > 0.0f)
    {
        const float DodgeStep = FMath::Min(DodgeRemaining, DeltaSeconds);
        DodgeRemaining = FMath::Max(0.0f, DodgeRemaining - DeltaSeconds);
        const FVector Delta = DodgeDirection * 1400.0f * DodgeStep;
        FHitResult Hit;
        // Sweep prevents dashing through the floor, pillars, or the boss body.
        AddActorWorldOffset(Delta, true, &Hit);
    }
    if (AttackRemaining > 0.0f)
    {
        AttackRemaining = FMath::Max(0.0f, AttackRemaining - DeltaSeconds);
        const float Progress = 1.0f - AttackRemaining / AttackDuration;
        WeaponPivot->SetRelativeRotation(FRotator(-20.0f - 65.0f * FMath::Sin(Progress * PI), 0.0f, 0.0f));
        if (!bAttackResolved && Progress >= 0.35f)
        {
            bAttackResolved = true;
            ResolveAttack();
        }
    }

    const float Speed = Oath == EShenjinOath::Gale ? 650.0f : 560.0f;
    GetCharacterMovement()->MaxWalkSpeed = CanAct() ? Speed : 0.0f;
    for (UStaticMeshComponent* Arm : DivineArms)
    {
        Arm->SetVisibility(DivineRemaining > 0.0f && IsAlive());
    }
    Body->SetVisibility(HitFlash <= 0.0f || FMath::Fmod(HitFlash, 0.1f) < 0.05f);

    // The first encounter uses a circular arena. Keep the capsule inside its edge.
    FVector Location = GetActorLocation();
    const FVector Planar(Location.X, Location.Y, 0.0f);
    if (Planar.SizeSquared() > FMath::Square(1700.0f))
    {
        const FVector Clamped = Planar.GetSafeNormal() * 1700.0f;
        Location.X = Clamped.X;
        Location.Y = Clamped.Y;
        SetActorLocation(Location);
    }
    if (Location.Z < -500.0f && IsAlive())
    {
        Health = 0.0f;
        if (AShenjinGameMode* Mode = Cast<AShenjinGameMode>(UGameplayStatics::GetGameMode(this)))
        {
            Mode->EndEncounter(false);
        }
    }
}

void AShenjinCharacter::Attack()
{
    if (!CanAct() || AttackRemaining > 0.0f || DodgeRemaining > 0.0f) return;
    AttackDuration = DivineRemaining > 0.0f ? 0.34f : (Oath == EShenjinOath::Gale ? 0.42f : 0.55f);
    AttackRemaining = AttackDuration;
    bAttackResolved = false;
    // A small facing assist makes a large static boss readable at close range.
    if (const AShenjinGameMode* Mode = Cast<AShenjinGameMode>(UGameplayStatics::GetGameMode(this)))
    {
        if (AShenjinSentinel* Boss = Mode->GetSentinel())
        {
            FVector Toward = Boss->GetActorLocation() - GetActorLocation();
            Toward.Z = 0.0f;
            if (Toward.SizeSquared() < FMath::Square(600.0f)) SetActorRotation(Toward.Rotation());
        }
    }
}

void AShenjinCharacter::ResolveAttack()
{
    if (!CanAct()) return;
    const AShenjinGameMode* Mode = Cast<AShenjinGameMode>(UGameplayStatics::GetGameMode(this));
    AShenjinSentinel* Boss = Mode ? Mode->GetSentinel() : nullptr;
    if (!Boss || !Boss->IsAlive()) return;
    FVector Toward = Boss->GetActorLocation() - GetActorLocation();
    Toward.Z = 0.0f;
    const float Reach = DivineRemaining > 0.0f ? 470.0f : 380.0f;
    if (Toward.SizeSquared() > FMath::Square(Reach)
        || FVector::DotProduct(GetActorForwardVector(), Toward.GetSafeNormal()) < 0.35f) return;
    const float OathDamage = Oath == EShenjinOath::Ember ? 44.0f : (Oath == EShenjinOath::Gale ? 31.0f : 32.0f);
    Boss->ReceiveStrike(OathDamage * (DivineRemaining > 0.0f ? 1.8f : 1.0f));
    if (DivineRemaining <= 0.0f) DivineCharge = FMath::Min(100.0f, DivineCharge + 12.0f);
}

void AShenjinCharacter::Dodge()
{
    if (!CanAct() || DodgeCooldown > 0.0f) return;
    DodgeDirection = GetLastMovementInputVector().GetSafeNormal2D();
    if (DodgeDirection.IsNearlyZero()) DodgeDirection = GetActorForwardVector();
    DodgeRemaining = 0.25f;
    DodgeCooldown = Oath == EShenjinOath::Gale ? 0.7f : 1.1f;
    AttackRemaining = 0.0f;
    WeaponPivot->SetRelativeRotation(FRotator(-20.0f, 0.0f, 0.0f));
    GetCharacterMovement()->StopMovementImmediately();
}

void AShenjinCharacter::ActivateDivineForm()
{
    if (!CanAct() || DivineCharge < 100.0f || DivineRemaining > 0.0f) return;
    DivineCharge = 0.0f;
    DivineRemaining = 8.0f;
}

void AShenjinCharacter::SwitchOath()
{
    if (!CanAct() || OathCooldown > 0.0f || AttackRemaining > 0.0f || DodgeRemaining > 0.0f) return;
    Oath = static_cast<EShenjinOath>((static_cast<uint8>(Oath) + 1) % 3);
    OathCooldown = 1.0f;
    UpdateOathVisual();
}

void AShenjinCharacter::UpdateOathVisual()
{
    const FLinearColor Color = Oath == EShenjinOath::Ember ? FLinearColor(1.0f, 0.28f, 0.04f)
        : (Oath == EShenjinOath::Aegis ? FLinearColor(0.12f, 0.8f, 1.0f) : FLinearColor(0.38f, 1.0f, 0.55f));
    for (UStaticMeshComponent* Arm : DivineArms) ShenjinVisuals::Tint(Arm, Color);
}

FString AShenjinCharacter::GetOathLabel() const
{
    switch (Oath)
    {
    case EShenjinOath::Aegis: return TEXT("AEGIS / 40% damage reduction");
    case EShenjinOath::Gale: return TEXT("GALE / faster movement and recovery");
    default: return TEXT("EMBER / stronger spear strikes");
    }
}

void AShenjinCharacter::ReceiveStrike(float Damage)
{
    if (!CanAct() || IsInvulnerable() || Damage <= 0.0f) return;
    const float Multiplier = Oath == EShenjinOath::Aegis ? 0.6f : 1.0f;
    Health = FMath::Max(0.0f, Health - Damage * Multiplier);
    HitFlash = 0.3f;
    if (!IsAlive())
    {
        AttackRemaining = 0.0f;
        GetCharacterMovement()->StopMovementImmediately();
        if (AShenjinGameMode* Mode = Cast<AShenjinGameMode>(UGameplayStatics::GetGameMode(this)))
        {
            Mode->EndEncounter(false);
        }
    }
}

void AShenjinCharacter::Restart()
{
    // Allowed during a fight as well as after victory or defeat.
    UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this, true)));
}
