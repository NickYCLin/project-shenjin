#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "ShenjinHUD.generated.h"

UCLASS()
class SHENJIN_API AShenjinHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};
