#include "ShenjinSentinel.h"

#include "ShenjinCharacter.h"
#include "ShenjinGameMode.h"
#include "ShenjinVisuals.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Kismet/GameplayStatics.h"

AShenjinSentinel::AShenjinSentinel()
{
    PrimaryActorTick.bCanEverTick = true;
    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(SceneRoot);
    Collision = CreateDefaultSubobject<UCapsuleComponent>(TEXT("BossCollision"));
    Collision->SetupAttachment(SceneRoot);
    Collision->InitCapsuleSize(140.0f, 280.0f);
    Collision->SetRelativeLocation(FVector(0.0f, 0.0f, 280.0f));
    Collision->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Collision->SetCollisionResponseToAllChannels(ECR_Ignore);
    Collision->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
    Collision->SetCollisionResponseToChannel(ECC_Camera, ECR_Block);

    Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SentinelVisual"));
    Body->SetupAttachment(SceneRoot);
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Telegraph = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StrikeArea"));
    Telegraph->SetupAttachment(SceneRoot);
    Telegraph->SetRelativeLocation(FVector(0.0f, 0.0f, 5.0f));
    Telegraph->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Telegraph->SetCastShadow(false);
}

void AShenjinSentinel::BeginPlay()
{
    Super::BeginPlay();
    if (UStaticMesh* Imported = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Shenjin/Meshes/sentinel.sentinel")))
    {
        Body->SetStaticMesh(Imported);
        Body->SetRelativeRotation(FRotator(0.0f, 90.0f, 0.0f));
        bImportedBody = true;
    }
    else
    {
        Body->SetStaticMesh(ShenjinVisuals::Shape(TEXT("Cube")));
        Body->SetRelativeLocation(FVector(0.0f, 0.0f, 300.0f));
        Body->SetRelativeScale3D(FVector(3.0f, 3.0f, 6.0f));
        ShenjinVisuals::Tint(Body, FLinearColor(0.22f, 0.27f, 0.29f));
    }
    Telegraph->SetStaticMesh(ShenjinVisuals::Shape(TEXT("Cylinder")));
    ShenjinVisuals::Tint(Telegraph, FLinearColor(1.0f, 0.075f, 0.012f));
    Telegraph->SetVisibility(false);
}

void AShenjinSentinel::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    HitFlash = FMath::Max(0.0f, HitFlash - DeltaSeconds);
    Body->SetVisibility(HitFlash <= 0.0f || FMath::Fmod(HitFlash, 0.1f) < 0.05f);
    if (State == ESentinelState::Dead)
    {
        const float Roll = FMath::FInterpTo(Body->GetRelativeRotation().Roll, -65.0f, DeltaSeconds, 1.5f);
        Body->SetRelativeRotation(FRotator(0.0f, bImportedBody ? 90.0f : 0.0f, Roll));
        return;
    }
    const AShenjinGameMode* Mode = Cast<AShenjinGameMode>(UGameplayStatics::GetGameMode(this));
    AShenjinCharacter* Hero = Cast<AShenjinCharacter>(UGameplayStatics::GetPlayerCharacter(this, 0));
    if (!Mode || Mode->IsEncounterOver() || !Hero || !Hero->IsAlive())
    {
        Telegraph->SetVisibility(false);
        return;
    }

    StateRemaining -= DeltaSeconds;
    if (State == ESentinelState::Approach)
    {
        FVector Direction = Hero->GetActorLocation() - GetActorLocation();
        Direction.Z = 0.0f;
        const float Distance = Direction.Size();
        if (Distance > 390.0f)
        {
            const float Step = FMath::Min(Distance - 390.0f, (IsPhaseTwo() ? 260.0f : 185.0f) * DeltaSeconds);
            FVector Next = GetActorLocation() + Direction.GetSafeNormal() * Step;
            const FVector Planar(Next.X, Next.Y, 0.0f);
            if (Planar.SizeSquared() > FMath::Square(1400.0f)) Next = Planar.GetSafeNormal() * 1400.0f;
            // Deliberately kinematic: this arena has no interior navigation obstacles.
            SetActorLocation(Next);
        }
        if (!Direction.IsNearlyZero()) SetActorRotation(Direction.Rotation());
        if (StateRemaining <= 0.0f && Distance <= 650.0f) StartTelegraph();
    }
    else if (State == ESentinelState::Telegraph)
    {
        // The full hazard footprint stays fixed for the entire windup.
        const float Pulse = 1.0f - FMath::Clamp(StateRemaining / TelegraphDuration, 0.0f, 1.0f);
        Telegraph->SetRelativeScale3D(FVector(GetStrikeRadius() / 50.0f, GetStrikeRadius() / 50.0f, 0.02f));
        Body->SetRelativeRotation(FRotator(-12.0f * Pulse, bImportedBody ? 90.0f : 0.0f, 0.0f));
        if (StateRemaining <= 0.0f) Slam();
    }
    else if (State == ESentinelState::Slam && StateRemaining <= 0.0f)
    {
        State = ESentinelState::Recover;
        StateRemaining = bChargedAttack ? 1.0f : 1.55f;
        Telegraph->SetVisibility(false);
        Body->SetRelativeRotation(FRotator(0.0f, bImportedBody ? 90.0f : 0.0f, 0.0f));
    }
    else if (State == ESentinelState::Recover && StateRemaining <= 0.0f)
    {
        State = ESentinelState::Approach;
        StateRemaining = 0.35f;
    }
}

void AShenjinSentinel::StartTelegraph()
{
    // Snapshot the phase when the attack begins: the radius cannot grow mid-cue.
    bChargedAttack = IsPhaseTwo();
    TelegraphDuration = bChargedAttack ? 0.9f : 1.2f;
    State = ESentinelState::Telegraph;
    StateRemaining = TelegraphDuration;
    Telegraph->SetRelativeScale3D(FVector(GetStrikeRadius() / 50.0f, GetStrikeRadius() / 50.0f, 0.02f));
    Telegraph->SetVisibility(true);
}

void AShenjinSentinel::Slam()
{
    State = ESentinelState::Slam;
    StateRemaining = 0.22f;
    Body->SetRelativeRotation(FRotator(12.0f, bImportedBody ? 90.0f : 0.0f, 0.0f));
    if (AShenjinCharacter* Hero = Cast<AShenjinCharacter>(UGameplayStatics::GetPlayerCharacter(this, 0)))
    {
        if (FVector::DistSquared2D(Hero->GetActorLocation(), GetActorLocation()) <= FMath::Square(GetStrikeRadius()))
        {
            Hero->ReceiveStrike(bChargedAttack ? 36.0f : 26.0f);
        }
    }
}

void AShenjinSentinel::ReceiveStrike(float Damage)
{
    if (!IsAlive() || Damage <= 0.0f) return;
    Health = FMath::Max(0.0f, Health - Damage * (State == ESentinelState::Recover ? 1.35f : 1.0f));
    HitFlash = 0.18f;
    if (Health <= 0.0f)
    {
        State = ESentinelState::Dead;
        Telegraph->SetVisibility(false);
        Collision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if (AShenjinGameMode* Mode = Cast<AShenjinGameMode>(UGameplayStatics::GetGameMode(this)))
        {
            Mode->EndEncounter(true);
        }
    }
}

FString AShenjinSentinel::GetStateLabel() const
{
    switch (State)
    {
    case ESentinelState::Telegraph: return bChargedAttack ? TEXT("CHARGED SLAM - CLEAR THE CIRCLE") : TEXT("SLAM INCOMING - DODGE OR MOVE OUT");
    case ESentinelState::Slam: return TEXT("IMPACT");
    case ESentinelState::Recover: return TEXT("EXPOSED - 35% BONUS DAMAGE");
    case ESentinelState::Dead: return TEXT("THE SENTINEL HAS FALLEN");
    default: return TEXT("THE SENTINEL APPROACHES");
    }
}
