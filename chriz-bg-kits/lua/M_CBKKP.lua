-- chriz-bg-kits Component 100: Multiclass kit WEAPPROF column redirect.
-- Coexists idempotently with chriz-bg-rebalance component 411 via _G.CBRKitProficiency.

CBRKitProficiency = CBRKitProficiency or { Status = "not initialized" }
CBKKitProficiency = CBRKitProficiency
local state = CBRKitProficiency
if state.queued or state.installed then return end
if not EEex_Active then
    state.Status = "EEex is required"
    print("CBK kit weapon lists: " .. state.Status)
    return
end

local entries = {}

function state.ShouldUseKitColumn(nClass, nKit)
    local byKit = entries[nClass]
    return byKit ~= nil and byKit[nKit] == true
end

function CBKKitProficiency_ShouldOverride(nClass, nKit)
    return state.ShouldUseKitColumn(nClass, nKit)
end

local function installHook()
    local registry = EEex_Resource_Load2DA("CBRKPKIT")
    if not registry then error("CBK kit weapon lists: CBRKPKIT.2DA missing") end
    local count = 0
    for row in EEex_Resource_Get2DARowTableIterator(registry, false) do
        local cls, kit = tonumber(row[1]), tonumber(row[2])
        if cls and kit and cls >= 1 and cls <= 255 and kit >= 0 then
            cls, kit = math.floor(cls), math.floor(kit)
            entries[cls] = entries[cls] or {}
            if not entries[cls][kit] then
                entries[cls][kit] = true
                count = count + 1
            end
        end
    end
    if count == 0 then
        state.Status = "no entries"
        return
    end
    local site = EEex_TryLabel("CBR-KitProficiencyColumn")
    if not site then
        state.Status = "missing CBR-KitProficiencyColumn pattern"
        print("CBK kit weapon lists: " .. state.Status)
        return
    end
    EEex_DisableCodeProtection()
    EEex_HookConditionalJumpOnSuccessWithLabels(site, 0, {
        {"hook_integrity_watchdog_ignore_registers", {
            EEex_HookIntegrityWatchdogRegister.RAX, EEex_HookIntegrityWatchdogRegister.RCX,
            EEex_HookIntegrityWatchdogRegister.RDX, EEex_HookIntegrityWatchdogRegister.R8,
            EEex_HookIntegrityWatchdogRegister.R9, EEex_HookIntegrityWatchdogRegister.R10,
            EEex_HookIntegrityWatchdogRegister.R11,
        }}},
        EEex_FlattenTable({
            {[[
                #MAKE_SHADOW_SPACE(48)
            ]]},
            EEex_GenLuaCall("CBKKitProficiency_ShouldOverride", {
                ["args"] = {
                    function(off) return {"mov qword ptr ss:[rsp+#$(1)], rbp", {off}, "#ENDL"} end,
                    function(off) return {"mov qword ptr ss:[rsp+#$(1)], rbx", {off}, "#ENDL"} end,
                },
                ["returnType"] = EEex_LuaCallReturnType.Boolean,
            }),
            {[[
                test eax, eax
                jnz use_kit_col
                #DESTROY_SHADOW_SPACE
                jmp #L(jmp_success)
                call_error:
                #DESTROY_SHADOW_SPACE
                jmp #L(jmp_success)
                use_kit_col:
                #DESTROY_SHADOW_SPACE
            ]]},
        })
    )
    EEex_EnableCodeProtection()
    state.installed = true
    state.Status = "installed (" .. tostring(count) .. " pairs)"
end

state.queued = true
EEex_GameState_AddInitializedListener(installHook)
