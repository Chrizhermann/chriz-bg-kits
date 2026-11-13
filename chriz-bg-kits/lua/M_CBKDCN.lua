-- chriz-bg-kits Component 320: Dual-Classes Keep Kit Names (pure EEex runtime).
-- Reads CBKDCNAM.2DA (CLASS ORIG_FLAG KIT MIXED LOWER) and updates
-- CDerivedStats m_nClassTypeOverrideMixed / m_nClassTypeOverrideLower when empty or ours.

CBKDualClassNames = CBKDualClassNames or { Status = "not initialized", map = {}, ownedStrrefs = {} }
local state = CBKDualClassNames

function state.LoadRows(rows)
    local map, owned = {}, {}
    for _, row in ipairs(rows or {}) do
        local cls = tonumber(row[1])
        local origFlag = tonumber(row[2])
        local kit = tonumber(row[3])
        local mixed = tonumber(row[4])
        local lower = tonumber(row[5])
        if cls and origFlag and kit and mixed and lower then
            cls = math.floor(cls)
            origFlag = math.floor(origFlag)
            kit = math.floor(kit)
            mixed = math.floor(mixed)
            lower = math.floor(lower)
            map[cls] = map[cls] or {}
            map[cls][origFlag] = map[cls][origFlag] or {}
            map[cls][origFlag][kit] = { mixed = mixed, lower = lower }
            owned[mixed] = true
        end
    end
    state.map = map
    state.ownedStrrefs = owned
end

function state.ApplyToSprite(sprite)
    local base = sprite.m_baseStats
    if not base then return end
    local dualFlag = EEex_BAnd(base.m_flags or 0, 0x1F8)
    if dualFlag == 0 then return end
    local cls = sprite.m_typeAI and sprite.m_typeAI.m_Class
    if not cls then return end
    local kit = EEex_BOr(EEex_LShift(base.m_mageSpecUpperWord or 0, 16), base.m_mageSpecialization or 0)
    if kit == 0 or kit == 0x4000 then return end

    local byClass = state.map[cls]
    local byOrig = byClass and byClass[dualFlag]
    local entry = byOrig and byOrig[kit]
    if not entry then return end

    local stats = sprite.m_derivedStats
    if not stats then return end
    local cur = stats.m_nClassTypeOverrideMixed or -1
    -- Never clobber foreign op290 titles (e.g. Eldritch Knight / Arcane Trickster)
    if cur == 0 or cur == -1 or cur == 0xFFFFFFFF or state.ownedStrrefs[cur] then
        stats.m_nClassTypeOverrideMixed = entry.mixed
        stats.m_nClassTypeOverrideLower = entry.lower
    end
end

if state.registered then return end
if not EEex_Active then
    state.Status = "EEex is required"
    return
end

local function load2da()
    local tbl = EEex_Resource_Load2DA("CBKDCNAM")
    if not tbl then return end
    local rows = {}
    for row in EEex_Resource_Get2DARowTableIterator(tbl, false) do
        rows[#rows + 1] = row
    end
    state.LoadRows(rows)
end

EEex_GameState_AddInitializedListener(load2da)
EEex_Opcode_AddListsResolvedListener(function(sprite)
    pcall(state.ApplyToSprite, sprite)
end)
state.registered = true
state.Status = "registered"
