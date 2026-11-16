-- chriz-bg-kits Component 100: Scoped combat CheckSave & Damage hook dispatcher.
-- Wraps CGameEffect::CheckSave and CGameEffectDamage::ApplyEffect so kit/racial
-- passives (Elementalist Primal Penetration, Tectonic Strikes, Human Second Wind)
-- inspect or adjust per-hit / per-effect stats without placing shared debuffs on targets.

CBKCombat = CBKCombat or {
    Status = "not initialized",
    checkSaveBefore = {},
    checkSaveAfter = {},
    damageBefore = {},
    damageAfter = {},
}
local state = CBKCombat

local function updateGate()
    local active = (#state.checkSaveBefore > 0) or (#state.checkSaveAfter > 0)
        or (#state.damageBefore > 0) or (#state.damageAfter > 0)
    state.hasListeners = active
    if state.gatePtr and EEex_WriteU8 then
        EEex_WriteU8(state.gatePtr, active and 1 or 0)
    end
end

function state.AddCheckSaveListener(beforeFn, afterFn)
    if beforeFn then state.checkSaveBefore[#state.checkSaveBefore + 1] = beforeFn end
    if afterFn then state.checkSaveAfter[#state.checkSaveAfter + 1] = afterFn end
    updateGate()
end

function state.AddDamageListener(beforeFn, afterFn)
    if beforeFn then state.damageBefore[#state.damageBefore + 1] = beforeFn end
    if afterFn then state.damageAfter[#state.damageAfter + 1] = afterFn end
    updateGate()
end

function CBKCombat_OnCheckSaveBefore(effPtr, targetPtr)
    if #state.checkSaveBefore == 0 then return end
    local okE, eff = pcall(EEex_PtrToUD, effPtr, "CGameEffect")
    local okT, tgt = pcall(EEex_PtrToUD, targetPtr, "CGameSprite")
    if not (okE and okT and eff and tgt) then return end
    for i = 1, #state.checkSaveBefore do
        pcall(state.checkSaveBefore[i], eff, tgt)
    end
end

function CBKCombat_OnCheckSaveAfter(effPtr, targetPtr)
    if #state.checkSaveAfter == 0 then return end
    local okE, eff = pcall(EEex_PtrToUD, effPtr, "CGameEffect")
    local okT, tgt = pcall(EEex_PtrToUD, targetPtr, "CGameSprite")
    for i = #state.checkSaveAfter, 1, -1 do
        pcall(state.checkSaveAfter[i], okE and eff or nil, okT and tgt or nil)
    end
end

function CBKCombat_OnDamageBefore(effPtr, sourcePtr, targetPtr)
    if #state.damageBefore == 0 then return end
    local okE, eff = pcall(EEex_PtrToUD, effPtr, "CGameEffect")
    local okS, src = false, nil
    if sourcePtr and sourcePtr ~= 0 then
        okS, src = pcall(EEex_PtrToUD, sourcePtr, "CGameSprite")
    end
    local okT, tgt = pcall(EEex_PtrToUD, targetPtr, "CGameSprite")
    if not (okE and okT and eff and tgt) then return end
    for i = 1, #state.damageBefore do
        pcall(state.damageBefore[i], eff, okS and src or nil, tgt)
    end
end

function CBKCombat_OnDamageAfter(effPtr, sourcePtr, targetPtr)
    if #state.damageAfter == 0 then return end
    local okE, eff = pcall(EEex_PtrToUD, effPtr, "CGameEffect")
    local okS, src = false, nil
    if sourcePtr and sourcePtr ~= 0 then
        okS, src = pcall(EEex_PtrToUD, sourcePtr, "CGameSprite")
    end
    local okT, tgt = pcall(EEex_PtrToUD, targetPtr, "CGameSprite")
    for i = #state.damageAfter, 1, -1 do
        pcall(state.damageAfter[i], okE and eff or nil, okS and src or nil, okT and tgt or nil)
    end
end

if state.queued or state.installed then return end
if not EEex_Active then
    state.Status = "EEex is required"
    return
end

local function installHooks()
    local cs1 = EEex_TryLabel("CBK-CheckSave-CS1")
    local cs2 = EEex_TryLabel("CBK-CheckSave-CS2")
    local dmgBefore = EEex_TryLabel("CBK-Damage-Before")
    local dmgAfter = EEex_TryLabel("CBK-Damage-After")
    if not (cs1 and cs2 and dmgBefore and dmgAfter) then
        state.Status = "missing CBKCMB pattern labels"
        print("CBK combat hooks: " .. state.Status)
        return
    end

    local gatePtr = EEex_Malloc(8)
    local ctxPtr = EEex_Malloc(32)
    state.gatePtr = gatePtr
    state.ctxPtr = ctxPtr
    if EEex_WriteU8 then
        EEex_WriteU8(gatePtr, state.hasListeners and 1 or 0)
    end

    EEex_DisableCodeProtection()

    for idx, site in ipairs({ cs1, cs2 }) do
        local sfx = "_cs" .. tostring(idx)
        EEex_HookBeforeAndAfterCallWithLabels(site, {
            {"hook_integrity_watchdog_ignore_registers_0", {
                EEex_HookIntegrityWatchdogRegister.RAX, EEex_HookIntegrityWatchdogRegister.R10,
                EEex_HookIntegrityWatchdogRegister.R11,
            }},
            {"hook_integrity_watchdog_ignore_registers_1", {
                EEex_HookIntegrityWatchdogRegister.RCX, EEex_HookIntegrityWatchdogRegister.RDX,
                EEex_HookIntegrityWatchdogRegister.R8, EEex_HookIntegrityWatchdogRegister.R9,
                EEex_HookIntegrityWatchdogRegister.R10, EEex_HookIntegrityWatchdogRegister.R11,
            }}},
            EEex_FlattenTable({
                {[[
                    cmp byte ptr ss:[#$(1)], 0 ]], {gatePtr}, [[ #ENDL
                    jz skip_before]] .. sfx .. [[ #ENDL
                    mov rax, #$(1) ]], {ctxPtr}, [[ #ENDL
                    mov qword ptr ds:[rax], rcx
                    mov qword ptr ds:[rax+8], rdx
                    #MAKE_SHADOW_SPACE(80)
                    mov qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)], rcx
                    mov qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-16)], rdx
                    mov qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-24)], r8
                    mov qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-32)], r9
                ]]},
                EEex_GenLuaCall("CBKCombat_OnCheckSaveBefore", {
                    ["labelSuffix"] = "_b" .. sfx,
                    ["args"] = {
                        function(off) return {
                            "mov rax, #$(1)", {ctxPtr}, "#ENDL",
                            "mov rcx, qword ptr ds:[rax]",
                            "mov qword ptr ss:[rsp+#$(1)], rcx", {off}, "#ENDL",
                        } end,
                        function(off) return {
                            "mov rax, #$(1)", {ctxPtr}, "#ENDL",
                            "mov rcx, qword ptr ds:[rax+8]",
                            "mov qword ptr ss:[rsp+#$(1)], rcx", {off}, "#ENDL",
                        } end,
                    },
                }),
                {[[
                    call_error_b]] .. sfx .. [[:
                    mov rcx, qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)]
                    mov rdx, qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-16)]
                    mov r8, qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-24)]
                    mov r9, qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-32)]
                    #DESTROY_SHADOW_SPACE
                    skip_before]] .. sfx .. [[:
                ]]},
            }),
            EEex_FlattenTable({
                {[[
                    cmp byte ptr ss:[#$(1)], 0 ]], {gatePtr}, [[ #ENDL
                    jz skip_after]] .. sfx .. [[ #ENDL
                    #MAKE_SHADOW_SPACE(64)
                    mov qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)], rax
                ]]},
                EEex_GenLuaCall("CBKCombat_OnCheckSaveAfter", {
                    ["labelSuffix"] = "_a" .. sfx,
                    ["args"] = {
                        function(off) return {
                            "mov rdx, #$(1)", {ctxPtr}, "#ENDL",
                            "mov rcx, qword ptr ds:[rdx]",
                            "mov qword ptr ss:[rsp+#$(1)], rcx", {off}, "#ENDL",
                        } end,
                        function(off) return {
                            "mov rdx, #$(1)", {ctxPtr}, "#ENDL",
                            "mov rcx, qword ptr ds:[rdx+8]",
                            "mov qword ptr ss:[rsp+#$(1)], rcx", {off}, "#ENDL",
                        } end,
                    },
                }),
                {[[
                    call_error_a]] .. sfx .. [[:
                    mov rax, qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)]
                    #DESTROY_SHADOW_SPACE
                    skip_after]] .. sfx .. [[:
                ]]},
            })
        )
    end

    EEex_HookAfterRestoreWithLabels(dmgBefore, 0, 6, 6, {
        {"hook_integrity_watchdog_ignore_registers", {
            EEex_HookIntegrityWatchdogRegister.RCX, EEex_HookIntegrityWatchdogRegister.RDX,
            EEex_HookIntegrityWatchdogRegister.R8, EEex_HookIntegrityWatchdogRegister.R9,
            EEex_HookIntegrityWatchdogRegister.R10, EEex_HookIntegrityWatchdogRegister.R11,
        }}},
        EEex_FlattenTable({
            {[[
                cmp byte ptr ss:[#$(1)], 0 ]], {gatePtr}, [[ #ENDL
                jz #L(return)
                #MAKE_SHADOW_SPACE(64)
                mov qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)], rax
            ]]},
            EEex_GenLuaCall("CBKCombat_OnDamageBefore", {
                ["labelSuffix"] = "_db",
                ["args"] = {
                    function(off) return {"mov qword ptr ss:[rsp+#$(1)], r14 #ENDL", {off}} end,
                    function(off) return {
                        "mov rax, qword ptr ss:[rbp-0x41]",
                        "mov qword ptr ss:[rsp+#$(1)], rax #ENDL", {off},
                    } end,
                    function(off) return {"mov qword ptr ss:[rsp+#$(1)], rbx #ENDL", {off}} end,
                },
            }),
            {[[
                call_error_db:
                mov rax, qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)]
                #DESTROY_SHADOW_SPACE
            ]]},
        })
    )

    EEex_HookAfterRestoreWithLabels(dmgAfter, 0, 8, 8, {
        {"hook_integrity_watchdog_ignore_registers", {
            EEex_HookIntegrityWatchdogRegister.RAX, EEex_HookIntegrityWatchdogRegister.RCX,
            EEex_HookIntegrityWatchdogRegister.RDX, EEex_HookIntegrityWatchdogRegister.R8,
            EEex_HookIntegrityWatchdogRegister.R9, EEex_HookIntegrityWatchdogRegister.R10,
            EEex_HookIntegrityWatchdogRegister.R11,
        }}},
        EEex_FlattenTable({
            {[[
                cmp byte ptr ss:[#$(1)], 0 ]], {gatePtr}, [[ #ENDL
                jz #L(return)
                #MAKE_SHADOW_SPACE(64)
                mov qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)], rax
            ]]},
            EEex_GenLuaCall("CBKCombat_OnDamageAfter", {
                ["labelSuffix"] = "_da",
                ["args"] = {
                    function(off) return {"mov qword ptr ss:[rsp+#$(1)], r14 #ENDL", {off}} end,
                    function(off) return {
                        "mov rax, qword ptr ss:[rbp-0x41]",
                        "mov qword ptr ss:[rsp+#$(1)], rax #ENDL", {off},
                    } end,
                    function(off) return {"mov qword ptr ss:[rsp+#$(1)], rbx #ENDL", {off}} end,
                },
            }),
            {[[
                call_error_da:
                mov rax, qword ptr ss:[rsp+#SHADOW_SPACE_BOTTOM(-8)]
                #DESTROY_SHADOW_SPACE
            ]]},
        })
    )

    EEex_EnableCodeProtection()
    state.installed = true
    state.Status = "installed"
end

state.queued = true
EEex_GameState_AddInitializedListener(installHooks)
