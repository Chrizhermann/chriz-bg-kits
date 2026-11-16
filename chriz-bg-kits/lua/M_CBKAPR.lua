-- chriz-bg-kits Component 100: Global Non-Warrior Proficiency APR.
-- Every non-warrior character wielding a weapon (proficiencyType 89..110 or 115,
-- excluding fighting styles 111..114) in which they hold >= 2 pips receives the exact
-- Pip APR delta from WSPATCK.2DA column 1: DecodeWSPATCK(WSPATCK[pips][1]) - DecodeWSPATCK(WSPATCK[1][1]).
-- Shares idempotence marker CBR_TEMPUS_SPEC_APR with M_CBRAPR.lua so no sprite double-dips.
-- Keeps CBKAPKIT.2DA harmlessly supported for backwards compatibility.

CBKSpecAPR = CBKSpecAPR or {
    Status = "not initialized",
    entries = {},
    pipDelta = { [0] = 0, [1] = 0, [2] = 0.5, [3] = 0.5, [4] = 0.5, [5] = 1.0 },
    maxPipRow = 5,
}
local state = CBKSpecAPR
local CBK_APR_STATE_ID = %CBK_APR_STATE_ID%
local MARKER_WORD = math.floor(CBK_APR_STATE_ID / 32)
local MARKER_MASK = EEex_LShift(1, CBK_APR_STATE_ID % 32)

-- Native warrior classes that already gain proficiency APR natively (CLSWPBON GETS_PROF_APR=1):
-- 2=Fighter, 6=Paladin, 7=Fighter/Mage, 8=Fighter/Cleric, 9=Fighter/Thief,
-- 10=Fighter/Mage/Thief, 12=Ranger, 16=Fighter/Druid, 17=Fighter/Mage/Cleric,
-- 18=Cleric/Ranger, 20=Monk
local WARRIOR_CLASSES = {
    [2] = true, [6] = true, [7] = true, [8] = true, [9] = true,
    [10] = true, [12] = true, [16] = true, [17] = true, [18] = true, [20] = true,
}

function state.DecodeAPR(key)
    if key <= 5 then return key end
    return (key - 6) + 0.5
end

function state.EncodeAPR(apr)
    if apr >= 5 then return 5 end
    local whole = math.floor(apr)
    if apr == whole then return whole end
    return 6 + whole
end

function state.DecodeWSPATCK(val)
    local n = tonumber(val) or 0
    if n == 0 then return 0 end
    if n > 0 then return n end
    return (-n) - 0.5
end

function state.LoadWSPATCKRows(rows)
    if not rows or #rows < 3 then
        state.pipDelta = { [0] = 0, [1] = 0, [2] = 0.5, [3] = 0.5, [4] = 0.5, [5] = 1.0 }
        state.maxPipRow = 5
        return
    end
    -- rows[1] = 0 pips, rows[2] = 1 pip, rows[3] = 2 pips, ... (bIncludeLabel = false -> col 1 is row[1])
    local baseOnePip = state.DecodeWSPATCK(rows[2] and rows[2][1] or 0)
    local delta = { [0] = 0, [1] = 0 }
    local maxPip = 1
    for idx = 3, #rows do
        local pips = idx - 1
        local raw = state.DecodeWSPATCK(rows[idx] and rows[idx][1] or 0)
        local d = raw - baseOnePip
        if d < 0 then d = 0 end
        delta[pips] = d
        maxPip = pips
    end
    state.pipDelta = delta
    state.maxPipRow = maxPip
end

function state.GetPipBonus(pips)
    if not pips or pips < 2 then return 0 end
    local idx = math.floor(pips)
    if idx > (state.maxPipRow or 5) then
        idx = state.maxPipRow or 5
    end
    return (state.pipDelta and state.pipDelta[idx]) or (idx >= 5 and 1.0 or 0.5)
end

function state.HasNativeWarriorSpec(nClass, baseFlags)
    if WARRIOR_CLASSES[nClass] then return true end
    -- Active/reactivated Fighter (0x08) or Ranger (0x100) dual-class original flags
    if EEex_BAnd(baseFlags or 0, 0x108) ~= 0 and EEex_BAnd(baseFlags or 0, 0x1000) == 0 then
        return true
    end
    return false
end

function state.LoadRows(rows)
    local out = {}
    for _, row in ipairs(rows or {}) do
        local kit = tonumber(row[1])
        local minPips = tonumber(row[2])
        local guard = tonumber(row[3])
        if kit and minPips and minPips >= 1 then
            out[math.floor(kit)] = {
                minPips = math.floor(minPips),
                warriorGuard = (guard or 1) ~= 0,
            }
        end
    end
    state.entries = out
end

local function applyToSprite(sprite)
    local stats = sprite.m_derivedStats
    if not stats then return end

    local states = stats.m_spellStates
    if not states then return end
    local word = states:get(MARKER_WORD)
    if EEex_BAnd(word, MARKER_MASK) ~= 0 then return end

    local kit = stats:GetAtOffset(0x98)
    if not kit then kit = stats.m_nKit end
    local cfg = state.entries[kit]
    local minPips = 2
    local warriorGuard = true
    if cfg then
        if cfg.minPips and cfg.minPips < minPips then
            minPips = cfg.minPips
        end
        warriorGuard = cfg.warriorGuard
    end

    if warriorGuard then
        local nClass = sprite.m_typeAI and sprite.m_typeAI.m_Class or 0
        local baseFlags = sprite.m_baseStats and sprite.m_baseStats.m_flags or 0
        if state.HasNativeWarriorSpec(nClass, baseFlags) then return end
    end

    local equipment = sprite.m_equipment
    if not equipment then return end
    local selected = equipment.m_selectedWeapon
    if selected == nil or selected < 0 or selected > 38 then return end
    local item = equipment.m_items:get(selected)
    if not item then return end
    if sprite.getLauncher then
        local abNum = equipment.m_selectedWeaponAbility or 0
        local ab = item.getAbility and item:getAbility(abNum) or nil
        if ab then
            item = sprite:getLauncher(ab) or item
        end
    end
    local res = item.pRes
    local header = res and res.pHeader
    if not header then return end
    local prof = header.proficiencyType
    if prof < 89 or prof > 115 or (prof >= 111 and prof <= 114) then return end

    local pips = stats:GetAtOffset(prof)
    if not pips or pips < minPips then return end

    local bonus = state.GetPipBonus(pips)
    if bonus <= 0 and pips >= minPips and minPips < 2 then
        bonus = 0.5
    end
    if bonus <= 0 then return end

    local key = stats.m_nNumberOfAttacks
    if key < 0 then return end

    states:set(MARKER_WORD, EEex_BOr(word, MARKER_MASK))
    if EEex_BAnd(stats.m_spellStates:get(MARKER_WORD), MARKER_MASK) == 0 then
        error("CBK spec APR: marker bit did not persist")
    end
    stats.m_nNumberOfAttacks = state.EncodeAPR(state.DecodeAPR(key) + bonus)
end

if state.registered then return end
if not EEex_Active then
    state.Status = "EEex is required"
    return
end

local function load2da()
    local wsp = EEex_Resource_Load2DA("WSPATCK")
    if wsp then
        local wspRows = {}
        for row in EEex_Resource_Get2DARowTableIterator(wsp, false) do
            wspRows[#wspRows + 1] = row
        end
        state.LoadWSPATCKRows(wspRows)
    end

    local tbl = EEex_Resource_Load2DA("CBKAPKIT")
    if tbl then
        local rows = {}
        for row in EEex_Resource_Get2DARowTableIterator(tbl, false) do
            rows[#rows + 1] = row
        end
        state.LoadRows(rows)
    end
end

EEex_GameState_AddInitializedListener(load2da)
local failures, dead = 0, false
EEex_Opcode_AddListsResolvedListener(function(sprite)
    if dead then return end
    local ok = pcall(applyToSprite, sprite)
    if not ok then
        failures = failures + 1
        if failures >= 10 then
            dead = true
            print("CBK spec APR: disabled after repeated errors")
        end
    end
end)
state.registered = true
state.Status = "registered"
