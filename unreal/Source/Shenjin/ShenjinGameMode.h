#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "ShenjinGameMode.generated.h"

class AShenjinSentinel;
class UStaticMesh;
class UMaterialInterface;

UCLASS()
class SHENJIN_API AShenjinGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    AShenjinGameMode();
    virtual void StartPlay() override;
    virtual void RestartPlayer(AController* NewPlayer) override;
    AShenjinSentinel* GetSentinel() const { return Sentinel; }
    bool IsEncounterOver() const { return bEncounterOver; }
    bool DidPlayerWin() const { return bPlayerWon; }
    void EndEncounter(bool bVictory);

private:
    void BuildArena();
    UPROPERTY()
    TObjectPtr<AShenjinSentinel> Sentinel;
    // Hard references make the cooker include the fallback assets used at runtime.
    UPROPERTY()
    TArray<TObjectPtr<UStaticMesh>> FallbackMeshes;
    UPROPERTY()
    TObjectPtr<UMaterialInterface> FallbackMaterial;
    bool bEncounterOver = false;
    bool bPlayerWon = false;
};
