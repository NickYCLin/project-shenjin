#include "ShenjinHUD.h"

#include "ShenjinCharacter.h"
#include "ShenjinGameMode.h"
#include "ShenjinSentinel.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Kismet/GameplayStatics.h"

void AShenjinHUD::DrawHUD()
{
    Super::DrawHUD();
    if (!Canvas || !GEngine) return;
    const AShenjinCharacter* Hero = Cast<AShenjinCharacter>(UGameplayStatics::GetPlayerCharacter(this, 0));
    const AShenjinGameMode* Mode = Cast<AShenjinGameMode>(UGameplayStatics::GetGameMode(this));
    if (!Hero || !Mode) return;
    const float Scale = FMath::Min(Canvas->ClipX / 1280.0f, Canvas->ClipY / 720.0f);
    const float Left = (Canvas->ClipX - 1280.0f * Scale) * 0.5f;
    const FLinearColor Gold(1.0f, 0.74f, 0.32f);
    auto Text = [this, Scale, Left](const FString& Value, float X, float Y, FLinearColor Color, float Size = 1.0f)
    {
        DrawText(Value, Color, Left + X * Scale, Y * Scale, GEngine->GetMediumFont(), Size * Scale, false);
    };
    auto Bar = [this, Scale, Left](float X, float Y, float Width, float Ratio, FLinearColor Color)
    {
        DrawRect(FLinearColor(0.01f, 0.025f, 0.03f, 0.92f), Left + X * Scale, Y * Scale, Width * Scale, 13.0f * Scale);
        DrawRect(Color, Left + X * Scale, Y * Scale, Width * Scale * FMath::Clamp(Ratio, 0.0f, 1.0f), 13.0f * Scale);
    };
    Text(TEXT("SHENJIN / LOST TEMPLE"), 36, 28, Gold, 1.15f);
    Text(TEXT("FIRST ENCOUNTER / SOLO PROTOTYPE"), 36, 56, FLinearColor(0.65f, 0.75f, 0.78f), 0.8f);
    if (const AShenjinSentinel* Boss = Mode->GetSentinel())
    {
        Text(Boss->IsPhaseTwo() ? TEXT("THE ASH SENTINEL / PHASE II") : TEXT("THE ASH SENTINEL"), 445, 33, Gold);
        Bar(395, 64, 500, Boss->GetHealthRatio(), FLinearColor(0.85f, 0.3f, 0.12f));
        Text(Boss->GetStateLabel(), 410, 86, FLinearColor::White, 0.8f);
    }
    Text(Hero->GetOathLabel(), 36, 571, Gold, 0.85f);
    Text(TEXT("VITALITY"), 36, 607, FLinearColor::White, 0.8f);
    Bar(130, 610, 255, Hero->GetHealthRatio(), FLinearColor(0.7f, 0.17f, 0.11f));
    Text(Hero->GetDivineSeconds() > 0.0f
        ? FString::Printf(TEXT("DIVINE FORM / %.1fs"), Hero->GetDivineSeconds())
        : FString::Printf(TEXT("DIVINE CHARGE / %.0f%%"), Hero->GetDivineCharge()), 36, 638, Gold, 0.8f);
    Bar(36, 662, 350, Hero->GetDivineSeconds() > 0.0f ? Hero->GetDivineSeconds() / 8.0f : Hero->GetDivineCharge() / 100.0f, Gold);
    Text(TEXT("WASD Move   Mouse Look   LMB / J Strike"), 720, 601, FLinearColor::White, 0.85f);
    Text(TEXT("Space Dodge   Q Divine Form   E Change Oath"), 720, 629, FLinearColor::White, 0.85f);
    const FString DodgeLabel = Hero->GetDodgeCooldown() <= 0.0f ? FString(TEXT("READY"))
        : FString::Printf(TEXT("%.1fs"), Hero->GetDodgeCooldown());
    Text(FString::Printf(TEXT("Dodge: %s   R Restart"), *DodgeLabel),
        720, 658, Gold, 0.85f);
    if (Hero->GetDivineCharge() >= 100.0f && Hero->GetDivineSeconds() <= 0.0f)
    {
        Text(TEXT("Q / AWAKEN YOUR DIVINE FORM"), 448, 536, Gold, 1.0f);
    }
    if (Mode->IsEncounterOver())
    {
        DrawRect(FLinearColor(0.008f, 0.02f, 0.026f, 0.88f), Left + 290 * Scale, 270 * Scale, 700 * Scale, 165 * Scale);
        Text(Mode->DidPlayerWin() ? TEXT("THE FIRST OATH IS FULFILLED") : TEXT("YOUR EMBER HAS FADED"), 390, 306, Gold, 1.4f);
        Text(Mode->DidPlayerWin() ? TEXT("Sentinel defeated. The temple remembers.") : TEXT("Watch the strike circle. Punish the recovery."),
            385, 355, FLinearColor::White, 0.95f);
        Text(TEXT("R / BEGIN AGAIN"), 545, 395, Gold);
    }
}
