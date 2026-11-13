-- chriz-bg-kits Component 100: Strength floor (CBM_STR_FLOOR / CBTSTRF) + CBK_STR_CLAMP_1.
-- Coexists safely with chriz-bg-magic M_CBMSTR.lua via CBMStrength.registered.

local FLOOR_STATE = %CBM_STR_FLOOR_STATE%
local CLAMP_STATE = %CBK_STR_CLAMP_1_STATE%
local TAG = "CBTSTRF"

CBMStrength = CBMStrength or {}
local S = CBMStrength

function S.ApplyFloor(sprite)
    local stats = sprite:getActiveStats()
    if stats:GetSpellState(FLOOR_STATE) == 0 then return end

    local bestStr, bestExtra = 0, 0
    local function consider(packed)
        if not packed or packed <= 0 then return end
        local s = math.floor(packed / 1000)
        local e = packed % 1000
        if s > bestStr or (s == bestStr and e > bestExtra) then
            bestStr, bestExtra = s, e
        end
    end

    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, function(eff)
        if eff.m_effectId == 328 and eff.m_dWFlags == FLOOR_STATE then
            consider(eff.m_special)
        end
    end)
    EEex_Utility_IterateCPtrList(sprite.m_equipedEffectList, function(eff)
        if eff.m_effectId == 328 and eff.m_dWFlags == FLOOR_STATE then
            consider(eff.m_special)
        end
    end)
    if bestStr == 0 then return end

    local curStr = stats.m_nSTR or 0
    local curExtra = stats.m_nSTRExtra or 0
    if curStr > bestStr or (curStr == bestStr and curExtra >= bestExtra) then return end

    local deltaStr = bestStr - curStr
    local deltaExtra = (bestExtra > 0) and (bestExtra - curExtra) or 0
    sprite:applyEffect({
        effectID = 44,
        effectAmount = deltaStr,
        dwFlags = 0,
        durationType = 9,
        noSave = 1,
        m_scriptName = TAG,
        immediateResolve = 1,
    })
    if deltaExtra > 0 then
        sprite:applyEffect({
            effectID = 97,
            effectAmount = deltaExtra,
            dwFlags = 0,
            durationType = 9,
            noSave = 1,
            m_scriptName = TAG,
            immediateResolve = 1,
        })
    end
end

function S.ClampStrOne(sprite)
    local stats = sprite.m_derivedStats
    if not stats then return end
    if stats:GetSpellState(CLAMP_STATE) == 0 then return end
    if (stats.m_nSTR or 1) < 1 then
        stats.m_nSTR = 1
    end
end

if not EEex_Active then return end

if not S.registered then
    EEex_Opcode_AddListsResolvedListener(function(sprite)
        pcall(S.ApplyFloor, sprite)
    end)
    S.registered = true
end

if not S.cbkClampRegistered then
    EEex_Opcode_AddListsResolvedListener(function(sprite)
        pcall(S.ClampStrOne, sprite)
    end)
    S.cbkClampRegistered = true
end
