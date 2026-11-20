-- M_CBKILM.lua: Painbearer of Ilmater (Component 205)
-- Enforces a non-additive 25% Physical Resistance floor (Slashing, Crushing, Piercing, Missile)
-- while CBK_ILMATER_ENDURE is active, guarded by idempotence marker CBK_ILM_RESOLVED.

CBKIlmater = CBKIlmater or {}
local state = CBKIlmater

state.stEndure   = tonumber("%CBK_STATE_ILMATER_ENDURE%") or -1
state.stResolved = tonumber("%CBK_STATE_ILM_RESOLVED%") or -1
state.FLOOR_DR   = 25

function state.HasSpellState(sprite, st)
    if not sprite or not st or st < 0 then return false end
    if sprite._spellStates and sprite._spellStates[st] ~= nil then
        return sprite._spellStates[st] == true
    end
    if type(EEex_Sprite_GetSpellState) == "function" then
        return EEex_Sprite_GetSpellState(sprite, st) == true
    end
    local ds = sprite.m_derivedStats
    if ds and ds.m_spellStates and st <= 255 then
        local word = math.floor(st / 32)
        local mask = (type(EEex_LShift) == "function") and EEex_LShift(1, st % 32) or bit.lshift(1, st % 32)
        local bandFn = (type(EEex_BAnd) == "function") and EEex_BAnd or bit.band
        return bandFn(ds.m_spellStates:get(word), mask) ~= 0
    end
    return false
end

function state.SetResolvedState(sprite, st)
    if not sprite or not st or st < 0 then return end
    if sprite._spellStates then
        sprite._spellStates[st] = true
    end
    local ds = sprite.m_derivedStats
    if ds and ds.m_spellStates and st <= 255 then
        local word = math.floor(st / 32)
        local mask = (type(EEex_LShift) == "function") and EEex_LShift(1, st % 32) or bit.lshift(1, st % 32)
        local borFn = (type(EEex_BOr) == "function") and EEex_BOr or bit.bor
        ds.m_spellStates:set(word, borFn(ds.m_spellStates:get(word), mask))
    end
end

local function maxFloor(cur, flr)
    cur = cur or 0
    if cur < flr then return flr end
    return cur
end

function state.OnListsResolved(sprite)
    if not sprite then return false end
    local ds = sprite.m_derivedStats
    if not ds then return false end
    if not state.HasSpellState(sprite, state.stEndure) then
        return false
    end
    if state.stResolved >= 0 and state.HasSpellState(sprite, state.stResolved) then
        return false
    end

    local flr = state.FLOOR_DR
    ds.m_nResistSlashing = maxFloor(ds.m_nResistSlashing, flr)
    ds.m_nResistCrushing = maxFloor(ds.m_nResistCrushing, flr)
    ds.m_nResistPiercing = maxFloor(ds.m_nResistPiercing, flr)
    ds.m_nResistMissile  = maxFloor(ds.m_nResistMissile,  flr)

    if state.stResolved >= 0 then
        state.SetResolvedState(sprite, state.stResolved)
    end
    return true
end

if not state.listenersRegistered then
    state.listenersRegistered = true
    if EEex_Opcode_AddListsResolvedListener then
        EEex_Opcode_AddListsResolvedListener(function(sprite)
            pcall(state.OnListsResolved, sprite)
        end)
    end
end
