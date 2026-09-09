#include "ShenjinGameMode.h"

#include "ShenjinCharacter.h"
#include "ShenjinHUD.h"
#include "ShenjinSentinel.h"
#include "ShenjinVisuals.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

AShenjinGameMode::AShenjinGameMode()
{
    DefaultPawnClass = AShenjinCharacter::StaticClass();
    HUDClass = AShenjinHUD::StaticClass();
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    FallbackMeshes = {Cube.Object, Sphere.Object, Cylinder.Object};
    FallbackMaterial = Material.Object;
}

void AShenjinGameMode::StartPlay()
{
    BuildArena();
    Sentinel = GetWorld()->SpawnActor<AShenjinSentinel>(AShenjinSentinel::StaticClass(),
        FVector(0.0f, 500.0f, 0.0f), FRotator(0.0f, -90.0f, 0.0f));
    Super::StartPlay();
}

void AShenjinGameMode::RestartPlayer(AController* NewPlayer)
{
    if (!NewPlayer) return;
    RestartPlayerAtTransform(NewPlayer, FTransform(FRotator(0.0f, 90.0f, 0.0f), FVector(0.0f, -800.0f, 100.0f)));
    NewPlayer->SetControlRotation(FRotator(-14.0f, 90.0f, 0.0f));
}

void AShenjinGameMode::EndEncounter(bool bVictory)
{
    if (bEncounterOver) return;
    bEncounterOver = true;
    bPlayerWon = bVictory;
}

void AShenjinGameMode::BuildArena()
{
    UWorld* World = GetWorld();
    auto AddMesh = [World](UStaticMesh* Mesh, const FVector& Location, const FVector& Scale,
        const FLinearColor& Color, bool bCollide) -> AStaticMeshActor*
    {
        AStaticMeshActor* Actor = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), Location, FRotator::ZeroRotator);
        if (!Actor) return nullptr;
        UStaticMeshComponent* Component = Actor->GetStaticMeshComponent();
        Component->SetMobility(EComponentMobility::Movable);
        Component->SetStaticMesh(Mesh);
        Component->SetWorldScale3D(Scale);
        Component->SetCollisionEnabled(bCollide ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
        if (bCollide) Component->SetCollisionProfileName(TEXT("BlockAll"));
        ShenjinVisuals::Tint(Component, Color);
        return Actor;
    };

    AStaticMeshActor* Floor = AddMesh(ShenjinVisuals::Shape(TEXT("Cylinder")),
        FVector(0.0f, 0.0f, -60.0f), FVector(36.0f, 36.0f, 1.2f), FLinearColor(0.13f, 0.17f, 0.18f), true);
    if (UStaticMesh* Temple = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Shenjin/Meshes/temple.temple")))
    {
        AStaticMeshActor* Environment = World->SpawnActor<AStaticMeshActor>();
        if (Environment)
        {
            Environment->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
            Environment->GetStaticMeshComponent()->SetStaticMesh(Temple);
            Environment->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            if (Floor) Floor->SetActorHiddenInGame(true);
        }
    }
    else
    {
        for (int32 Index = 0; Index < 12; ++Index)
        {
            const float Angle = Index * 2.0f * PI / 12.0f;
            AddMesh(ShenjinVisuals::Shape(TEXT("Cube")),
                FVector(FMath::Cos(Angle) * 1700.0f, FMath::Sin(Angle) * 1700.0f, 400.0f),
                FVector(1.5f, 1.5f, 8.0f), FLinearColor(0.23f, 0.2f, 0.15f), true);
        }
        AddMesh(ShenjinVisuals::Shape(TEXT("Sphere")), FVector(0.0f, 2800.0f, 900.0f),
            FVector(14.0f, 9.0f, 18.0f), FLinearColor(0.2f, 0.25f, 0.27f), false);
    }

    World->SpawnActor<ASkyAtmosphere>();
    if (ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>(ADirectionalLight::StaticClass(),
        FVector(0.0f, 0.0f, 2200.0f), FRotator(-35.0f, -30.0f, 0.0f)))
    {
        UDirectionalLightComponent* Light = CastChecked<UDirectionalLightComponent>(Sun->GetLightComponent());
        Light->SetMobility(EComponentMobility::Movable);
        Light->SetIntensity(5.0f);
        Light->SetLightColor(FLinearColor(1.0f, 0.76f, 0.5f));
        Light->bAtmosphereSunLight = true;
    }
    if (ASkyLight* Sky = World->SpawnActor<ASkyLight>())
    {
        Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
        Sky->GetLightComponent()->SetIntensity(1.2f);
        Sky->GetLightComponent()->SetRealTimeCaptureEnabled(true);
    }
    if (AExponentialHeightFog* Fog = World->SpawnActor<AExponentialHeightFog>())
    {
        Fog->GetComponent()->SetFogDensity(0.012f);
        Fog->GetComponent()->SetFogInscatteringColor(FLinearColor(0.09f, 0.18f, 0.22f));
    }
}
