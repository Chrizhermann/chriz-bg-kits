-- chriz-bg-kits Component 100: Table-driven CInfGame::CheckItemUsableByClass override.
-- Reads CBKWPN.2DA (CLASS, KIT, TARGET_TYPE [PROF|ITEMTYPE|SUBTYPE], TARGET_ID, RULE [ALLOW|DENY]).
-- DENY takes precedence over ALLOW; unmatched items fall through to original engine result.
-- Also removes redundant Barbarian kit usability blocks on non-Fighter items for dual-classed Barbarians.

CBKWeaponUsability = CBKWeaponUsability or { Status = "not initialized", rules = {} }
local state = CBKWeaponUsability

-- ITM V1 0x1E race usability bits:
local RACE_UNUSABLE_BIT = {
    [1] = 0x08000000, -- HUMAN
    [2] = 0x00800000, -- ELF
    [3] = 0x04000000, -- HALF_ELF
    [4] = 0x01000000, -- DWARF
    [5] = 0x02000000, -- HALFLING
    [6] = 0x10000000, -- GNOME
    [7] = 0x80000000, -- HALFORC
}

-- ITM V1 0x1E dual-class unusable bits for Fighter/Barbarian dual-classes:
local DUAL_CLASS_UNUSABLE_BIT = {
    [7]  = 0x00002000, -- FIGHTER_MAGE
    [8]  = 0x00004000, -- FIGHTER_CLERIC
    [9]  = 0x00020000, -- FIGHTER_THIEF
    [16] = 0x00001000, -- FIGHTER_DRUID
}

local function toU32(n)
    if not n then return 0 end
    if n < 0 then return n + 4294967296 end
    return n
end

local function parseRuleId(tok)
    if tok == "*" then return nil end
    local n = tonumber(tok)
    if not n then return nil end
    return toU32(math.floor(n))
end

local function isBlockedByRace(unus, nRace)
    if not unus or not nRace then return false end
    local mask = RACE_UNUSABLE_BIT[nRace]
    if not mask then return false end
    return EEex_BAnd(unus, mask) ~= 0
end

local function extractHeaderMeta(hdr)
    if not hdr then return 0, "", 0 end
    local unus = hdr.notUsableBy
    local anim = hdr.anim
    local minStr = hdr.minStrength

    local ptr = nil
    if EEex_UDToPtr then
        local ok, p = pcall(EEex_UDToPtr, hdr)
        if ok and type(p) == "number" and p ~= 0 then
            ptr = p
        end
    end

    if unus == nil and ptr and EEex_ReadU32 then
        unus = EEex_ReadU32(ptr + 0x1E)
    end
    if anim == nil then
        local rawAnim = hdr.animationType
        if type(rawAnim) == "string" then
            anim = rawAnim
        elseif ptr and EEex_ReadU8 then
            local b1 = EEex_ReadU8(ptr + 0x22)
            local b2 = EEex_ReadU8(ptr + 0x23)
            anim = string.char(b1 or 32, b2 or 32)
        else
            anim = ""
        end
    end
    if minStr == nil and ptr and EEex_ReadU16 then
        minStr = EEex_ReadU16(ptr + 0x26)
    end
    return toU32(unus or 0), tostring(anim or ""), tonumber(minStr) or 0
end

local function isRobeAnim(anim)
    return anim == "2W" or anim == "3W" or anim == "4W"
end

local function isTowerShield(anim, minStr)
    return anim == "C2" or anim == "C5" or anim == "C6" or anim == "D4" or minStr >= 15
end

-- SUBTYPE IDs in CBKWPN.2DA:
-- 1: Non-robe body armor (itemType == 2 and anim not in 2W/3W/4W)
-- 2: Armor <= Chain Mail (2A leather/hide, or 3A chain usable by Bard [0x40==0], Fighter-usable & race-usable)
-- 3: Heavy armor >= Splint Mail (4A plate/full plate, or 3A splint [0x40~=0])
-- 4: Buckler / Small / Medium Shield (itemType == 12, non-tower, Fighter-usable & race-usable)
-- 5: Tower / Large Shield (itemType == 12 and C2/C5/C6/D4 or minStr >= 15)
-- 6: Mage Robe (itemType == 2, anim in 2W/3W/4W, Mage-usable [0x40000==0] & race-usable)
-- 7: Helmet usable by Fighter & race (itemType == 7, [0x0800==0] & race-usable)
local function matchSubtype(subtypeId, itemType, unus, anim, minStr, nRace)
    if subtypeId == 1 then
        return itemType == 2 and not isRobeAnim(anim)
    elseif subtypeId == 2 then
        if itemType ~= 2 then return false end
        if isBlockedByRace(unus, nRace) or EEex_BAnd(unus, 0x0800) ~= 0 then return false end
        if anim == "2A" then return true end
        if anim == "3A" and EEex_BAnd(unus, 0x0040) == 0 then return true end
        return false
    elseif subtypeId == 3 then
        if itemType ~= 2 then return false end
        return anim == "4A" or (anim == "3A" and EEex_BAnd(unus, 0x0040) ~= 0)
    elseif subtypeId == 4 then
        if itemType ~= 12 then return false end
        if isTowerShield(anim, minStr) then return false end
        if isBlockedByRace(unus, nRace) or EEex_BAnd(unus, 0x0800) ~= 0 then return false end
        return true
    elseif subtypeId == 5 then
        return itemType == 12 and isTowerShield(anim, minStr)
    elseif subtypeId == 6 then
        if itemType ~= 2 or not isRobeAnim(anim) then return false end
        if isBlockedByRace(unus, nRace) or EEex_BAnd(unus, 0x00040000) ~= 0 then return false end
        return true
    elseif subtypeId == 7 then
        if itemType ~= 7 then return false end
        if isBlockedByRace(unus, nRace) or EEex_BAnd(unus, 0x0800) ~= 0 then return false end
        return true
    end
    return false
end

function state.LoadRulesFromRows(rows)
    local rules = {}
    for _, row in ipairs(rows or {}) do
        local cls = parseRuleId(row[1])
        local kit = parseRuleId(row[2])
        local ttype = string.upper(tostring(row[3] or ""))
        local tid = tonumber(row[4])
        local rule = string.upper(tostring(row[5] or ""))
        if (ttype == "PROF" or ttype == "ITEMTYPE" or ttype == "SUBTYPE")
            and tid and (rule == "ALLOW" or rule == "DENY")
        then
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

function state.EvaluateRule(nClass, nKit, profType, itemType, origUsable, hdr, nRace)
    local normKit = toU32(nKit)
    local unus, anim, minStr = extractHeaderMeta(hdr)
    local seenAllow = false

    for _, r in ipairs(state.rules) do
        local clsOk = (r.classId == nil) or (r.classId == nClass)
        local kitOk = (r.kitId == nil) or (r.kitId == normKit)
        if clsOk and kitOk then
            local targetOk = false
            if r.targetType == "PROF" then
                targetOk = (r.targetId == profType)
                if targetOk and r.rule == "ALLOW" and hdr and isBlockedByRace(unus, nRace) then
                    targetOk = false
                end
            elseif r.targetType == "ITEMTYPE" then
                targetOk = (r.targetId == itemType)
                if targetOk and r.rule == "ALLOW" and hdr and isBlockedByRace(unus, nRace) then
                    targetOk = false
                end
            elseif r.targetType == "SUBTYPE" then
                targetOk = matchSubtype(r.targetId, itemType, unus, anim, minStr, nRace)
            end
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

    -- Dual-classed Barbarian (0x40000000): allow items of their new class (robes, scrolls, wands, etc.)
    -- that set Fighter unusable (0x0800) + redundant Barbarian kit mirror bit, while keeping heavy armor blocked.
    if origUsable == 0 and normKit == 0x40000000 and hdr then
        local dcBit = DUAL_CLASS_UNUSABLE_BIT[nClass]
        if dcBit and EEex_BAnd(unus, 0x0800) ~= 0 and EEex_BAnd(unus, dcBit) == 0 and not isBlockedByRace(unus, nRace) then
            return 1
        end
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

function CBKWeaponUsability_NativeEval(itemPtr, nClass, nKit, origUsable, nRace)
    local ok, item = pcall(EEex_PtrToUD, itemPtr, "CItem")
    if not ok or not item then return origUsable end
    local res = item.pRes
    if not res then return origUsable end
    local hdr = res.pHeader
    if not hdr then return origUsable end
    return state.EvaluateRule(nClass, nKit, hdr.proficiencyType, hdr.itemType, origUsable, hdr, nRace)
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
                        function(off) return {
                            "mov rdx, #$(1)", {ctxPtr}, "#ENDL",
                            "mov ecx, dword ptr ds:[rdx+12]",
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
