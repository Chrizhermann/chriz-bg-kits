-- M_CBKSHR.lua: Priest of Shar (Component 202)
-- Shadow Weave Magic: applies a scoped -2 saving throw penalty on targets of
-- Enchantment (4), Illusion (5), and Necromancy (7) spells — plus Shadow Bolt
-- (CBKSHR2) — cast by a Priest of Shar (spell state CBK_SHAR_WEAVE or kit
-- CBK_SHAR), excluding item effects (m_sourceType == 2). Restores exact
-- original m_saveMod immediately after CheckSave via stack-safe LIFO frames.

CBKShar = CBKShar or {}
local state = CBKShar

state.kitIds       = tonumber("%CBK_SHAR_KIT_IDS%") or -1
state.stWeave      = tonumber("%CBK_STATE_SHAR_WEAVE%") or -1
state.SAVE_PENALTY = 2

state.SHADOW_SCHOOLS = {
    [4] = true, -- Enchantment
    [5] = true, -- Illusion
    [7] = true, -- Necromancy
}

state.spellSchoolCache = state.spellSchoolCache or {}

local function isCallable(v)
    local t = type(v)
    return t == "function" or t == "userdata"
end

function state.HasSpellState(sprite, st)
    if not sprite or not st or st < 0 then return false end
    if sprite._spellStates and sprite._spellStates[st] ~= nil then
        return sprite._spellStates[st] == true
    end
    if isCallable(EEex_Sprite_GetSpellState) then
        return EEex_Sprite_GetSpellState(sprite, st) == true
    end
    local ds = sprite.m_derivedStats
    if ds and ds.m_spellStates and st <= 255 and isCallable(ds.m_spellStates.get) then
        local word = math.floor(st / 32)
        local mask = isCallable(EEex_LShift) and EEex_LShift(1, st % 32) or bit.lshift(1, st % 32)
        local bandFn = isCallable(EEex_BAnd) and EEex_BAnd or bit.band
        return bandFn(ds.m_spellStates:get(word) or 0, mask) ~= 0
    end
    return false
end

function state.GetSpriteKitIds(sprite)
    if not sprite then return 0 end
    if sprite._kitIds ~= nil then return sprite._kitIds end
    local bs = sprite.m_baseStats
    if bs and bs.m_mageSpecUpperWord ~= nil and bs.m_mageSpecialization ~= nil then
        local hi = bit.band(bs.m_mageSpecUpperWord, 0xFFFF)
        local lo = bit.band(bs.m_mageSpecialization, 0xFFFF)
        return bit.bor(bit.lshift(hi, 16), lo)
    end
    if isCallable(EEex_Sprite_GetStat) then
        return EEex_Sprite_GetStat(sprite, 152) or 0
    end
    return 0
end

function state.IsShadowWeaver(sprite)
    if not sprite then return false end
    if state.stWeave >= 0 and state.HasSpellState(sprite, state.stWeave) then
        return true
    end
    if state.kitIds >= 0 and state.GetSpriteKitIds(sprite) == state.kitIds then
        return true
    end
    return false
end

function state.GetEffectSourceRes(effect)
    if not effect then return "" end
    local sr = effect.m_sourceRes
    if type(sr) == "string" then return sr:upper() end
    if sr and isCallable(sr.get) then return (sr:get() or ""):upper() end
    return ""
end

function state.GetSpellSchool(resref)
    if type(resref) ~= "string" or resref == "" then return 0 end
    local up = resref:upper()
    if state.mockSpellSchools and state.mockSpellSchools[up] ~= nil then
        return state.mockSpellSchools[up]
    end
    if state.spellSchoolCache[up] ~= nil then
        return state.spellSchoolCache[up]
    end
    local school = 0
    if isCallable(EEex_Resource_Demand) then
        local ok, hdr = pcall(EEex_Resource_Demand, up, "SPL")
        if ok and hdr then
            if hdr.primaryType ~= nil then
                school = hdr.primaryType
            elseif hdr.school ~= nil then
                school = hdr.school
            elseif isCallable(EEex_UDToPtr) and isCallable(EEex_ReadU8) then
                local okP, ptr = pcall(EEex_UDToPtr, hdr)
                if okP and type(ptr) == "number" and ptr ~= 0 then
                    school = EEex_ReadU8(ptr + 0x25) or 0
                end
            end
        end
    end
    state.spellSchoolCache[up] = school
    return school
end

function state.IsShadowWeaveEffect(effect)
    if not effect then return false end
    local stype = effect.m_sourceType
    if stype == 2 then return false end -- item source, not a spell
    local sres = state.GetEffectSourceRes(effect)
    if sres == "CBKSHR2" then
        return true
    end
    if sres ~= "" then
        return state.SHADOW_SCHOOLS[state.GetSpellSchool(sres)] == true
    end
    return false
end

-- Shadow Weave Magic CheckSave listener:
-- Subtracts 2 from effect.m_saveMod before CGameEffect::CheckSave and restores exact origSaveMod after.
function state.OnCheckSaveBefore(srcSprite, tgtSprite, effect, ctx)
    if not srcSprite or not effect or not ctx then return end
    if not state.IsShadowWeaver(srcSprite) then return end
    if not state.IsShadowWeaveEffect(effect) then return end
    local orig = effect.m_saveMod or 0
    ctx.sharSavedMod = orig
    effect.m_saveMod = orig - state.SAVE_PENALTY
end

function state.OnCheckSaveAfter(srcSprite, tgtSprite, effect, ctx)
    if ctx and ctx.sharSavedMod ~= nil and effect then
        effect.m_saveMod = ctx.sharSavedMod
        ctx.sharSavedMod = nil
    end
end

if not state.listenersRegistered then
    state.listenersRegistered = true

    if CBKCombat and isCallable(CBKCombat.AddCheckSaveListener) then
        local csStack = {}
        local function resolveSource(eff)
            if not eff then return nil end
            if eff._sourceSprite then return eff._sourceSprite end
            if eff.m_sourceId and eff.m_sourceId ~= 0 and eff.m_sourceId ~= -1
                and isCallable(EEex_GameObject_Get) then
                local ok, sp = pcall(EEex_GameObject_Get, eff.m_sourceId)
                if ok and sp and (not isCallable(EEex_GameObject_IsSprite) or EEex_GameObject_IsSprite(sp, true)) then
                    return sp
                end
            end
            return nil
        end

        CBKCombat.AddCheckSaveListener(
            function(eff, tgt)
                local ctx = {}
                local src = resolveSource(eff)
                csStack[#csStack + 1] = { src = src, tgt = tgt, eff = eff, ctx = ctx }
                state.OnCheckSaveBefore(src, tgt, eff, ctx)
            end,
            function(eff, tgt)
                local frame = csStack[#csStack]
                csStack[#csStack] = nil
                if frame then
                    state.OnCheckSaveAfter(frame.src, tgt or frame.tgt, eff or frame.eff, frame.ctx)
                end
            end
        )
    end
end
