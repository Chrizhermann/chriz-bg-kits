-- chriz-bg-kits Component 100: Table-driven CInfGame::CheckItemUsableByClass override.
-- Reads CBKWPN.2DA (CLASS, KIT, TARGET_TYPE [PROF|ITEMTYPE], TARGET_ID, RULE [ALLOW|DENY]).
-- DENY takes precedence over ALLOW; unmatched items fall through to original engine result.

CBKWeaponUsability = CBKWeaponUsability or { Status = "not initialized", rules = {} }
local state = CBKWeaponUsability

local function parseRuleId(tok)
    if tok == "*" then return nil end
    local n = tonumber(tok)
    if not n then return nil end
    return math.floor(n)
end

function state.LoadRulesFromRows(rows)
    local rules = {}
    for _, row in ipairs(rows or {}) do
        local cls = parseRuleId(row[1])
        local kit = parseRuleId(row[2])
        local ttype = string.upper(tostring(row[3] or ""))
        local tid = tonumber(row[4])
        local rule = string.upper(tostring(row[5] or ""))
        if (ttype == "PROF" or ttype == "ITEMTYPE") and tid and (rule == "ALLOW" or rule == "DENY") then
            rules[#rules + 1] = {
                classId = cls,
                kitId = kit,
                targetType = ttype,
                targetId = math.floor(tid),
                rule = rule,
            }
        end
    end
    state.rules = rules
end

function state.EvaluateRule(nClass, nKit, profType, itemType, origUsable)
    local seenAllow = false
    for _, r in ipairs(state.rules) do
        local clsOk = (r.classId == nil) or (r.classId == nClass)
        local kitOk = (r.kitId == nil) or (r.kitId == nKit)
        if clsOk and kitOk then
            local targetOk = (r.targetType == "PROF" and r.targetId == profType)
                or (r.targetType == "ITEMTYPE" and r.targetId == itemType)
            if targetOk then
                if r.rule == "DENY" then
                    return 0
                elseif r.rule == "ALLOW" then
                    seenAllow = true
                end
            end
        end
    end
    if seenAllow then
        return 1
    end
    return origUsable
end

if state.queued or state.installed then return end
if not EEex_Active then
    state.Status = "EEex is required"
    print("CBK weapon usability: " .. state.Status)
    return
end

local function loadTable()
    local tbl = EEex_Resource_Load2DA("CBKWPN")
    if not tbl then error("CBK weapon usability: CBKWPN.2DA missing") end
    local rows = {}
    for row in EEex_Resource_Get2DARowTableIterator(tbl, false) do
        rows[#rows + 1] = row
    end
    state.LoadRulesFromRows(rows)
end

function CBKWeaponUsability_NativeEval(itemPtr, nClass, nKit, origUsable)
    local ok, item = pcall(EEex_PtrToUD, itemPtr, "CItem")
    if not ok or not item then return origUsable end
    local res = item.pRes
    if not res then return origUsable end
    local hdr = res.pHeader
    if not hdr then return origUsable end
    return state.EvaluateRule(nClass, nKit, hdr.proficiencyType, hdr.itemType, origUsable)
end

local function installHooks()
    loadTable()
    local sites = {
        EEex_TryLabel("CBK-CheckItemUsable-CS1"),
        EEex_TryLabel("CBK-CheckItemUsable-CS2"),
        EEex_TryLabel("CBK-CheckItemUsable-CS3"),
    }
    if not (sites[1] and sites[2] and sites[3]) then
        state.Status = "missing CBKWPN pattern labels"
        print("CBK weapon usability: " .. state.Status)
        return
    end
    local ctxPtr = EEex_Malloc(32)
    state.ctxPtr = ctxPtr
    EEex_DisableCodeProtection()
    for _, site in ipairs(sites) do
        EEex_HookBeforeAndAfterCallWithLabels(site, {
            {"hook_integrity_watchdog_ignore_registers_0", {EEex_HookIntegrityWatchdogRegister.RAX}},
            {"hook_integrity_watchdog_ignore_registers_1", {
                EEex_HookIntegrityWatchdogRegister.RAX, EEex_HookIntegrityWatchdogRegister.RCX,
                EEex_HookIntegrityWatchdogRegister.RDX, EEex_HookIntegrityWatchdogRegister.R8,
                EEex_HookIntegrityWatchdogRegister.R9, EEex_HookIntegrityWatchdogRegister.R10,
                EEex_HookIntegrityWatchdogRegister.R11,
            }}},
            {[[
                mov rax, #$(1) ]], {ctxPtr}, [[ #ENDL
                mov qword ptr ds:[rax], rdx
                mov dword ptr ds:[rax+8], r8d
                mov dword ptr ds:[rax+12], r9d
            ]]},
            EEex_FlattenTable({
                {[[
                    mov rdx, #$(1) ]], {ctxPtr}, [[ #ENDL
                    mov dword ptr ds:[rdx+16], eax
                    mov r8d, dword ptr ss:[rsp+38h]
                    mov dword ptr ds:[rdx+20], r8d
                    mov r9, qword ptr ss:[rsp+30h]
                    mov qword ptr ds:[rdx+24], r9
                    #MAKE_SHADOW_SPACE(64)
                ]]},
                EEex_GenLuaCall("CBKWeaponUsability_NativeEval", {
                    ["labelSuffix"] = "_1",
                    ["args"] = {
                        function(off) return {
                            "mov rdx, #$(1)", {ctxPtr}, "#ENDL",
                            "mov rcx, qword ptr ds:[rdx]",
                            "mov qword ptr ss:[rsp+#$(1)], rcx", {off}, "#ENDL",
                        } end,
                        function(off) return {
                            "mov rdx, #$(1)", {ctxPtr}, "#ENDL",
                            "mov ecx, dword ptr ds:[rdx+8]",
                            "mov qword ptr ss:[rsp+#$(1)], rcx", {off}, "#ENDL",
                        } end,
                        function(off) return {
                            "mov rdx, #$(1)", {ctxPtr}, "#ENDL",
                            "mov ecx, dword ptr ds:[rdx+20]",
                            "mov qword ptr ss:[rsp+#$(1)], rcx", {off}, "#ENDL",
                        } end,
                        function(off) return {
                            "mov rdx, #$(1)", {ctxPtr}, "#ENDL",
                            "mov ecx, dword ptr ds:[rdx+16]",
                            "mov qword ptr ss:[rsp+#$(1)], rcx", {off}, "#ENDL",
                        } end,
                    },
                    ["returnType"] = EEex_LuaCallReturnType.Number,
                }),
                {[[
                    jmp done_1
                    call_error_1:
                    mov rdx, #$(1) ]], {ctxPtr}, [[ #ENDL
                    mov eax, dword ptr ds:[rdx+16]
                    jmp skip_strref_1
                    done_1:
                    mov rdx, #$(1) ]], {ctxPtr}, [[ #ENDL
                    mov rcx, qword ptr ds:[rdx+24]
                    test rcx, rcx
                    jz skip_strref_1
                    cmp eax, 0
                    je set_deny_strref_1
                    mov dword ptr ds:[rcx], 0
                    jmp skip_strref_1
                    set_deny_strref_1:
                    cmp dword ptr ds:[rcx], 0
                    jne skip_strref_1
                    mov dword ptr ds:[rcx], 0F00029h
                    skip_strref_1:
                    #DESTROY_SHADOW_SPACE
                ]]},
            })
        )
    end
    EEex_EnableCodeProtection()
    state.installed = true
    state.Status = "installed (" .. tostring(#state.rules) .. " rules)"
end

state.queued = true
EEex_GameState_AddInitializedListener(installHooks)
