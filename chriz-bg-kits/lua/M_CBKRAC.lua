-- chriz-bg-kits Components 110 & 111: Racial Perks & Dual-Class Target Filter.
-- Perks:
--   Human (1)    : Second Wind (once/rest via save-persistent LOCALS "CBKSWND", <25% HP -> heal 20%, clear Fatigue/Fear)
--   Elf (2)      : +1 Save vs. Spell (m_nSaveVSSpell - 1 idempotently)
--   Half-Elf (3) : Silver Tongue (+10 Lore idempotently; +1 CHA & 50% Sleep/Charm res in 2DA/SPL)
--   Halfling (5) : Halfling Finesse (melee Dagger 96, Short Sword 91, Club 115, Scimitar 95 when DEX > STR)
-- UI Filter:
--   Dual-classing in CHARGEN_CLASS filters chargen.class against CLSRCREQ.2DA for the character's race.

CBKRaces = CBKRaces or {
    Status = "not initialized",
    strMod = nil,
    strModEx = nil,
    clsRcReq = {},
    raceIdToCol = {
        [1] = "HUMAN",
        [2] = "ELF",
        [3] = "HALF_ELF",
        [4] = "DWARF",
        [5] = "HALFLING",
        [6] = "GNOME",
        [7] = "HALFORC",
    },
}
local state = CBKRaces

local CBK_RAC_RESOLVED_STATE = %CBK_RAC_RESOLVED_STATE%
local MARKER_WORD = math.floor(CBK_RAC_RESOLVED_STATE / 32)
local MARKER_MASK = EEex_LShift(1, CBK_RAC_RESOLVED_STATE % 32)

local FINESSE_PROFS = {
    [91]  = true, -- SHORTSWORD
    [95]  = true, -- SCIMITARWAKISASHININJATO
    [96]  = true, -- DAGGER
    [115] = true, -- CLUB
}

local DUAL_TARGET_CLASS_NAME = {
    [1]  = "MAGE",
    [2]  = "FIGHTER",
    [3]  = "CLERIC",
    [4]  = "THIEF",
    [11] = "DRUID",
    [12] = "RANGER",
}

local DEFAULT_STRMOD = {
    [0]  = { -5, -4 }, [1]  = { -5, -4 }, [2]  = { -3, -2 }, [3]  = { -3, -1 },
    [4]  = { -2, -1 }, [5]  = { -2, -1 }, [6]  = { -1,  0 }, [7]  = { -1,  0 },
    [8]  = {  0,  0 }, [9]  = {  0,  0 }, [10] = {  0,  0 }, [11] = {  0,  0 },
    [12] = {  0,  0 }, [13] = {  0,  0 }, [14] = {  0,  0 }, [15] = {  0,  0 },
    [16] = {  0,  1 }, [17] = {  1,  1 }, [18] = {  1,  2 }, [19] = {  3,  7 },
    [20] = {  3,  8 }, [21] = {  4,  9 }, [22] = {  4, 10 }, [23] = {  5, 11 },
    [24] = {  6, 12 }, [25] = {  7, 14 },
}

local function defaultStrModEx(ex)
    if not ex or ex <= 0 then return 0, 0 end
    if ex <= 50 then return 0, 1 end
    if ex <= 75 then return 1, 1 end
    if ex <= 90 then return 1, 2 end
    if ex <= 99 then return 1, 3 end
    return 2, 4
end

function state.GetFinesseBonus(dex)
    local d = math.floor(tonumber(dex) or 0)
    if d < 16 then return 0, 0 end
    if d == 16 then return 0, 1 end
    if d == 17 then return 1, 1 end
    if d == 18 then return 2, 3 end
    if d == 19 then return 2, 4 end
    return 3, 5
end

function state.GetStrengthBonus(str, strEx)
    local s = math.max(0, math.min(25, math.floor(tonumber(str) or 0)))
    local ex = math.max(0, math.min(100, math.floor(tonumber(strEx) or 0)))
    local base = (state.strMod and state.strMod[s]) or DEFAULT_STRMOD[s] or { 0, 0 }
    local hit, dmg = base[1] or 0, base[2] or 0
    if s == 18 and ex > 0 then
        if state.strModEx and state.strModEx[ex] then
            hit = hit + (state.strModEx[ex][1] or 0)
            dmg = dmg + (state.strModEx[ex][2] or 0)
        else
            local eh, ed = defaultStrModEx(ex)
            hit = hit + eh
            dmg = dmg + ed
        end
    end
    return hit, dmg
end

local function getLocalInt(sprite, key)
    if EEex_Sprite_GetLocalInt then
        local ok, v = pcall(EEex_Sprite_GetLocalInt, sprite, key)
        if ok and type(v) == "number" then return v end
    end
    if sprite._locals then
        return sprite._locals[key] or 0
    end
    return 0
end

local function setLocalInt(sprite, key, val)
    if EEex_Sprite_SetLocalInt then
        pcall(EEex_Sprite_SetLocalInt, sprite, key, val)
    end
    if sprite._locals then
        sprite._locals[key] = val
    end
end

function state.ResetSecondWind(sprite)
    if not sprite then return end
    local race = sprite.m_typeAI and sprite.m_typeAI.m_Race or 0
    if race == 1 or getLocalInt(sprite, "CBKSWND") ~= 0 then
        setLocalInt(sprite, "CBKSWND", 0)
    end
end

function state.TrySecondWind(sprite)
    if not sprite then return false end
    local typeAI = sprite.m_typeAI
    if not typeAI or typeAI.m_Race ~= 1 then return false end
    local baseStats = sprite.m_baseStats
    if not baseStats then return false end
    if EEex_BAnd(baseStats.m_generalState or 0, 0xFC0) ~= 0 then return false end

    local curHP = tonumber(baseStats.m_hitPoints) or 0
    if curHP <= 0 then return false end

    local maxHP = 0
    if sprite.m_derivedStats and sprite.m_derivedStats.m_nMaxHitPoints then
        maxHP = tonumber(sprite.m_derivedStats.m_nMaxHitPoints) or 0
    elseif EEex_Sprite_GetStat then
        local ok, v = pcall(EEex_Sprite_GetStat, sprite, 1)
        if ok and type(v) == "number" then maxHP = v end
    end
    if maxHP <= 0 then return false end

    local belowQuarter = (curHP * 4 < maxHP) or (maxHP <= 4 and curHP == 1 and curHP < maxHP)
    if not belowQuarter then return false end

    if getLocalInt(sprite, "CBKSWND") ~= 0 then return false end
    setLocalInt(sprite, "CBKSWND", 1)

    local healAmt = math.max(1, math.floor(maxHP * 0.20 + 0.5))
    baseStats.m_fatigue = 0
    if sprite.m_derivedStats and sprite.m_derivedStats.m_nFatigue ~= nil then
        sprite.m_derivedStats.m_nFatigue = 0
    end

    if sprite.applyEffect then
        pcall(sprite.applyEffect, sprite, {
            effectID = 17,
            effectAmount = healAmt,
            dwFlags = 0,
            durationType = 1,
            noSave = 1,
            immediateResolve = 1,
        })
        pcall(sprite.applyEffect, sprite, {
            effectID = 146,
            dwFlags = 1,
            durationType = 1,
            noSave = 1,
            res = "CBKSWND",
            immediateResolve = 1,
        })
    end

    if (tonumber(baseStats.m_hitPoints) or 0) == curHP then
        baseStats.m_hitPoints = math.min(maxHP, curHP + healAmt)
    end
    return true
end

function state.ApplyRacialStats(sprite)
    if not sprite then return end
    local stats = sprite.m_derivedStats
    if not stats then return end
    local states = stats.m_spellStates
    if not states then return end

    local word = states:get(MARKER_WORD)
    if EEex_BAnd(word, MARKER_MASK) ~= 0 then return end

    local race = sprite.m_typeAI and sprite.m_typeAI.m_Race or 0
    if race ~= 2 and race ~= 3 and race ~= 5 then return end

    states:set(MARKER_WORD, EEex_BOr(word, MARKER_MASK))
    if EEex_BAnd(stats.m_spellStates:get(MARKER_WORD), MARKER_MASK) == 0 then
        error("CBK racial stats: marker bit did not persist")
    end

    if race == 2 then
        -- Elf: +1 Save vs. Spell (lower save value is better)
        stats.m_nSaveVSSpell = (stats.m_nSaveVSSpell or 0) - 1
    elseif race == 3 then
        -- Half-Elf Silver Tongue: +10 Lore
        stats.m_nLore = (stats.m_nLore or 0) + 10
    elseif race == 5 then
        -- Halfling Finesse: melee Dagger (96), Short Sword (91), Club (115), Scimitar (95) when DEX > STR
        local dex = tonumber(stats.m_nDEX) or 0
        local str = tonumber(stats.m_nSTR) or 0
        if dex <= str or dex < 16 then return end

        local equipment = sprite.m_equipment
        if not equipment then return end
        local selected = equipment.m_selectedWeapon
        if selected == nil or selected < 0 or selected > 38 then return end
        local item = equipment.m_items and equipment.m_items:get(selected)
        if not item then return end

        local abNum = equipment.m_selectedWeaponAbility or 0
        local ab = item.getAbility and item:getAbility(abNum) or nil
        if ab and (ab.type or 1) ~= 1 then return end

        local header = item.pRes and item.pRes.pHeader
        if not header or not FINESSE_PROFS[header.proficiencyType] then return end

        local finHit, finDmg = state.GetFinesseBonus(dex)
        local strHit, strDmg = state.GetStrengthBonus(str, stats.m_nSTRExtra)
        local dHit = math.max(0, finHit - strHit)
        local dDmg = math.max(0, finDmg - strDmg)

        if dHit > 0 then
            if stats.m_nMeleeTHAC0Bonus ~= nil then
                stats.m_nMeleeTHAC0Bonus = stats.m_nMeleeTHAC0Bonus + dHit
            elseif stats.m_nTHAC0 ~= nil then
                stats.m_nTHAC0 = stats.m_nTHAC0 - dHit
            end
        end
        if dDmg > 0 then
            if stats.m_nMeleeDamageBonus ~= nil then
                stats.m_nMeleeDamageBonus = stats.m_nMeleeDamageBonus + dDmg
            elseif stats.m_nDamageBonus ~= nil then
                stats.m_nDamageBonus = stats.m_nDamageBonus + dDmg
            end
        end
    end
end

function state.LoadCLSRCREQRows(headerCols, rows)
    local out = {}
    for _, row in ipairs(rows or {}) do
        local rowName = string.upper(tostring(row[1] or ""))
        if rowName ~= "" then
            local byRace = {}
            for i, colName in ipairs(headerCols or {}) do
                local rc = string.upper(tostring(colName or ""))
                byRace[rc] = tonumber(row[i + 1]) or 0
            end
            out[rowName] = byRace
        end
    end
    state.clsRcReq = out
end

function state.FilterDualClassTable(classList, raceId)
    if type(classList) ~= "table" then return end
    local raceCol = state.raceIdToCol[raceId]
    if not raceCol then return end
    for i = #classList, 1, -1 do
        local entry = classList[i]
        local clsId = entry and tonumber(entry.id)
        local clsName = clsId and DUAL_TARGET_CLASS_NAME[clsId]
        if clsName and state.clsRcReq[clsName] then
            local allowed = state.clsRcReq[clsName][raceCol]
            if allowed == 0 then
                table.remove(classList, i)
            end
        end
    end
end

if state.registered then return end
if not EEex_Active then
    state.Status = "EEex is required"
    return
end

local function loadTables()
    local sm = EEex_Resource_Load2DA and EEex_Resource_Load2DA("STRMOD")
    if sm then
        local map = {}
        for row in EEex_Resource_Get2DARowTableIterator(sm, true) do
            local k = tonumber(row[1])
            if k then
                map[math.floor(k)] = { tonumber(row[2]) or 0, tonumber(row[3]) or 0 }
            end
        end
        if next(map) then state.strMod = map end
    end

    local smx = EEex_Resource_Load2DA and EEex_Resource_Load2DA("STRMODEX")
    if smx then
        local mapEx = {}
        for row in EEex_Resource_Get2DARowTableIterator(smx, true) do
            local k = tonumber(row[1])
            if k then
                mapEx[math.floor(k)] = { tonumber(row[2]) or 0, tonumber(row[3]) or 0 }
            end
        end
        if next(mapEx) then state.strModEx = mapEx end
    end

    -- Load dynamic RACE.IDS symbols if available (e.g. HOBGOBLIN from chriz-bg-playable-races)
    if EEex_Resource_LoadIDS then
        local okIds, rids = pcall(EEex_Resource_LoadIDS, "RACE")
        if okIds and rids and rids.getCount then
            -- Optional EEex IDS object support; fallback keeps 1..7 + HOBGOBLIN lookup
        end
    end
    if EEex_Resource_Load2DA then
        local rcTbl = EEex_Resource_Load2DA("CLSRCREQ")
        if rcTbl then
            local hdr = state.clsRcHdr or nil
            if not hdr then
                if rcTbl.getColumnCount and rcTbl.getColumnLabel then
                    hdr = {}
                    local cc = rcTbl:getColumnCount()
                    for c = 0, cc - 1 do
                        hdr[#hdr + 1] = rcTbl:getColumnLabel(c)
                    end
                else
                    hdr = { "HUMAN", "ELF", "HALF_ELF", "DWARF", "HALFLING", "GNOME", "HALFORC", "HOBGOBLIN" }
                end
            end
            local rows = {}
            for row in EEex_Resource_Get2DARowTableIterator(rcTbl, true) do
                rows[#rows + 1] = row
            end
            state.LoadCLSRCREQRows(hdr, rows)
        end
    end
end

local function hookDualClassMenu()
    if not (EEex_Menu_Find and EEex_Menu_GetItemFunction and EEex_Menu_SetItemFunction) then return end
    local menu = EEex_Menu_Find("CHARGEN_CLASS")
    if not menu or not menu.reference_onOpen then return end
    local existingOnOpen = EEex_Menu_GetItemFunction(menu.reference_onOpen)
    EEex_Menu_SetItemFunction(menu.reference_onOpen, function()
        if existingOnOpen ~= nil then existingOnOpen() end
        local isDual = false
        if createCharScreen and const and createCharScreen.GetCurrentStep then
            local okS, step = pcall(createCharScreen.GetCurrentStep, createCharScreen)
            if okS and step == const.STEP_DUALCLASS_CLASS then isDual = true end
        elseif CurrentlyInGame then
            local okG, inGame = pcall(CurrentlyInGame)
            if okG and inGame then isDual = true end
        end
        if isDual and chargen and type(chargen.class) == "table" and currentID and EEex_GameObject_Get then
            local okSp, sp = pcall(EEex_GameObject_Get, currentID)
            local raceId = okSp and sp and sp.m_typeAI and sp.m_typeAI.m_Race
            if raceId then
                state.FilterDualClassTable(chargen.class, raceId)
            end
        end
    end)
end

-- Populate dynamic custom race IDs injected at install time (e.g. HOBGOBLIN)
%CBK_EXTRA_RACE_IDS%

EEex_GameState_AddInitializedListener(loadTables)

if EEex_Menu_AddAfterMainFileLoadedListener then
    EEex_Menu_AddAfterMainFileLoadedListener(hookDualClassMenu)
end

if CBKCombat and CBKCombat.AddDamageListener then
    CBKCombat.AddDamageListener(nil, function(_eff, _src, tgt)
        if tgt then
            state.TrySecondWind(tgt)
        end
    end)
end

if not state._restResetRegistered and EEex_Sprite_AddQuickListCountsResetListener then
    state._restResetRegistered = true
    EEex_Sprite_AddQuickListCountsResetListener(function(sprite)
        if CBKRaces and CBKRaces.ResetSecondWind then
            pcall(CBKRaces.ResetSecondWind, sprite)
        end
    end)
end

local failures, dead = 0, false
EEex_Opcode_AddListsResolvedListener(function(sprite)
    if dead then return end
    local ok = pcall(state.ApplyRacialStats, sprite)
    if not ok then
        failures = failures + 1
        if failures >= 10 then
            dead = true
            print("CBK racial stats: disabled after repeated errors")
        end
    end
end)

state.registered = true
state.Status = "registered"
