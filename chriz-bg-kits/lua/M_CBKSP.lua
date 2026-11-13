-- chriz-bg-kits Component 100: Kit-specific native bard spellbook progression (API 1).
-- Coexists idempotently with chriz-bg-rebalance component 420 via _G.CBRSpellProgression.

CBRSpellProgression = CBRSpellProgression or { API = 1, Status = "not initialized" }
CBKSpellProgression = CBRSpellProgression
local state = CBRSpellProgression
if state.queued or state.installed then return end
if not EEex_Active then
    state.Status = "EEex is required"
    print("CBK bard progression: " .. state.Status)
    return
end

local function installHook()
    local ver = EEex_Resource_Load2DA("CBRSPVER")
    if not ver or ver:getAtLabels("VALUE", "API") ~= "1" then
        error("CBK bard progression: unsupported CBRSPVER API")
    end
    local reg = EEex_Resource_Load2DA("CBRSPKIT")
    if not reg then error("CBK bard progression: CBRSPKIT.2DA missing") end

    state.tables = {}
    state.kits = {}
    local count = 0
    for row in EEex_Resource_Get2DARowTableIterator(reg, false) do
        local cls = tonumber(row[1])
        local kit = tonumber(row[2])
        local tname = string.upper(tostring(row[3] or ""))
        if cls == 5 and kit and tname ~= "" then
            if not state.tables[tname] then
                state.tables[tname] = EEex_Resource_Load2DA(tname)
            end
            if state.tables[tname] then
                state.kits[math.floor(kit)] = state.tables[tname]
                count = count + 1
            end
        end
    end
    if count == 0 then
        state.Status = "no registered bard kits"
        return
    end
    local site = EEex_TryLabel("CBR-BardSpellTable")
    if not site then
        state.Status = "missing CBR-BardSpellTable pattern"
        print("CBK bard progression: " .. state.Status)
        return
    end

    function CBKSpellProgression_ResolveTable(nKit)
        local ud = state.kits[nKit]
        if not ud then return 0 end
        return EEex_UDToPtr(ud)
    end

    EEex_DisableCodeProtection()
    EEex_HookAfterRestoreWithLabels(site, 0, 7, 7, {
        {"hook_integrity_watchdog_ignore_registers", {
            EEex_HookIntegrityWatchdogRegister.RAX, EEex_HookIntegrityWatchdogRegister.RCX,
            EEex_HookIntegrityWatchdogRegister.RDX, EEex_HookIntegrityWatchdogRegister.R8,
            EEex_HookIntegrityWatchdogRegister.R9, EEex_HookIntegrityWatchdogRegister.R10,
            EEex_HookIntegrityWatchdogRegister.R11,
        }}},
        EEex_FlattenTable({
            {[[
                #MAKE_SHADOW_SPACE(40)
                mov qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)], rcx
            ]]},
            EEex_GenLuaCall("CBKSpellProgression_ResolveTable", {
                ["args"] = {
                    function(off) return {"mov qword ptr ss:[rsp+#$(1)], rbx", {off}, "#ENDL"} end,
                },
                ["returnType"] = EEex_LuaCallReturnType.Number,
            }),
            {[[
                jmp ok_ret
                call_error:
                xor rax, rax
                ok_ret:
                test rax, rax
                jz keep_orig
                mov rcx, rax
                jmp finish_ret
                keep_orig:
                mov rcx, qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)]
                finish_ret:
                #DESTROY_SHADOW_SPACE
            ]]},
        })
    )
    EEex_EnableCodeProtection()
    state.installed = true
    state.Status = "installed (" .. tostring(count) .. " kits)"
end

state.queued = true
EEex_GameState_AddInitializedListener(installHook)
