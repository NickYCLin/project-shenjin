#pragma once

#include "CoreMinimal.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/UObjectGlobals.h"

// Generated project material is optional. The engine fallback stays visible even
// before prepare_project.py has created the custom tint material.
namespace ShenjinVisuals
{
    inline void Tint(UStaticMeshComponent* Component, const FLinearColor& Color)
    {
        UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
            TEXT("/Game/Shenjin/Materials/M_Prototype.M_Prototype"));
        if (!Material)
        {
            Material = LoadObject<UMaterialInterface>(nullptr,
                TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
        }
        if (Material)
        {
            UMaterialInstanceDynamic* Instance = UMaterialInstanceDynamic::Create(Material, Component);
            Instance->SetVectorParameterValue(TEXT("Tint"), Color);
            Instance->SetVectorParameterValue(TEXT("Color"), Color);
            Component->SetMaterial(0, Instance);
        }
    }

    inline UStaticMesh* Shape(const TCHAR* Name)
    {
        return LoadObject<UStaticMesh>(nullptr,
            *FString::Printf(TEXT("/Engine/BasicShapes/%s.%s"), Name, Name));
    }
}
