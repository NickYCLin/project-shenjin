#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "UObject/UObjectGlobals.h"

// Asset names are the prepare_animation.py contract. Owning actors keep Clips in
// a UPROPERTY map; /Game/Shenjin is explicitly included by the packaging config.
namespace ShenjinAnimation
{
    inline bool Load(USkeletalMeshComponent* Mesh, const TCHAR* Character,
        const TArray<FName>& Required, TMap<FName, TObjectPtr<UAnimSequence>>& Clips)
    {
        const FString Folder = FString::Printf(TEXT("/Game/Shenjin/Characters/%s"), Character);
        const FString Name = FString::Printf(TEXT("%s_SK"), Character);
        USkeletalMesh* Asset = LoadObject<USkeletalMesh>(nullptr,
            *FString::Printf(TEXT("%s/%s.%s"), *Folder, *Name, *Name));
        if (!Asset) return false;
        for (const FName Clip : Required)
        {
            const FString ClipName = FString::Printf(TEXT("%s_%s"), Character, *Clip.ToString());
            UAnimSequence* Animation = LoadObject<UAnimSequence>(nullptr,
                *FString::Printf(TEXT("%s/%s.%s"), *Folder, *ClipName, *ClipName));
            if (!Animation || Animation->GetSkeleton() != Asset->GetSkeleton()
                || Animation->GetPlayLength() <= KINDA_SMALL_NUMBER)
            {
                UE_LOG(LogTemp, Warning, TEXT("Shenjin: missing/incompatible %s; using static fallback"), *ClipName);
                Clips.Empty();
                return false;
            }
            Clips.Add(Clip, Animation);
        }
        Mesh->SetSkeletalMesh(Asset);
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        Mesh->SetVisibility(true);
        return true;
    }

    inline void Play(USkeletalMeshComponent* Mesh,
        const TMap<FName, TObjectPtr<UAnimSequence>>& Clips, FName& Current,
        FName Desired, bool bLoop, float Rate = 1.0f, bool bRestart = false)
    {
        const TObjectPtr<UAnimSequence>* Found = Clips.Find(Desired);
        if (!Found || !Found->Get()) return;
        // Never call PlayAnimation repeatedly while a state remains active.
        if (Current != Desired || bRestart)
        {
            Current = Desired;
            Mesh->PlayAnimation(Found->Get(), bLoop);
        }
        Mesh->SetPlayRate(Rate);
    }

    inline void OneShot(USkeletalMeshComponent* Mesh,
        const TMap<FName, TObjectPtr<UAnimSequence>>& Clips, FName& Current,
        FName Desired, float Duration, float Elapsed, bool bRestart = false)
    {
        const TObjectPtr<UAnimSequence>* Found = Clips.Find(Desired);
        if (!Found || !Found->Get()) return;
        const float Rate = Found->Get()->GetPlayLength() / FMath::Max(Duration, KINDA_SMALL_NUMBER);
        Play(Mesh, Clips, Current, Desired, false, Rate, bRestart);
        // Align pose to the gameplay timer (including cancelled attacks and low FPS).
        // SetPosition changes playback time, not animation mode or state.
        Mesh->SetPosition(FMath::Clamp(Elapsed * Rate, 0.0f, Found->Get()->GetPlayLength()), false);
    }
}
