using UnrealBuildTool;

public class ShenjinTarget : TargetRules
{
    public ShenjinTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V5;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_6;
        ExtraModuleNames.Add("Shenjin");
    }
}
