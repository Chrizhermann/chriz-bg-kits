-- M_CBKELM.lua: Elementalist Druid Kit (Component 220)
-- 1. Idempotent stat & non-additive resistance floors in ListsResolved (STR, DEX, Elemental Res, Physical DR).
-- 2. Shared daily charge pool across CBKELF1..4 (2/3/4/5/5 uses/day at L3/7/10/12/15).
-- 3. Tidal Healing 1-for-1 memorized spell swap in Water Form (SPPR Cure Wounds <-> CBKWTH1..6, preserving m_flags).
-- 4. Primal Penetration HLA via CBKCombat scoped CheckSave & Damage listeners (zero shared debuff on target).

CBKElementalist = CBKElementalist or {}
local state = CBKElementalist

state.kitIds     = tonumber("%CBK_ELM_KIT_IDS%") or -1
state.stFire     = tonumber("%CBK_STATE_ELM_FIRE%") or -1
state.stWater    = tonumber("%CBK_STATE_ELM_WATER%") or -1
state.stAir      = tonumber("%CBK_STATE_ELM_AIR%") or -1
state.stEarth    = tonumber("%CBK_STATE_ELM_EARTH%") or -1
state.stHla      = tonumber("%CBK_STATE_ELM_HLA%") or -1
state.stResolved = tonumber("%CBK_STATE_ELM_RESOLVED%") or -1

state.RACE_ELEMENTAL = 145
state.DMG_CRUSHING   = 0x00000000
state.DMG_ACID       = 0x00010000
state.DMG_COLD       = 0x00020000
state.DMG_ELEC       = 0x00040000
state.DMG_FIRE       = 0x00080000

state.FORM_ELEM_FLAG = {
    [1] = 0x00080000, -- Fire  -> Fire
    [2] = 0x00020000, -- Water -> Cold
    [3] = 0x00040000, -- Air   -> Electricity
    [4] = 0x00010000, -- Earth -> Acid
}

state.FORM_SHAPES = { "CBKELF1", "CBKELF2", "CBKELF3", "CBKELF4" }

state.FORM_FLOORS = {
    -- 1: Fire Form
    [1] = {
        str     = { 16, 17, 18, 18 },
        dex     = { 16, 17, 18, 19 },
        fire    = { 50, 75, 90, 100 },
        phys    = { 0,  10, 15, 20 },
    },
    -- 2: Water Form
    [2] = {
        str     = { 18, 19, 20, 21 },
        dex     = { 16, 17, 18, 19 },
        cold    = { 50, 75, 90, 100 },
        fire    = { 0,  25, 50, 50 },
        phys    = { 10, 15, 20, 25 },
    },
    -- 3: Air Form
    [3] = {
        str     = { 16, 17, 18, 18 },
        dex     = { 18, 19, 20, 21 },
        elec    = { 50, 75, 90, 100 },
        missile = { 20, 40, 50, 60 },
        phys    = { 0,  10, 15, 20 },
    },
    -- 4: Earth Form
    [4] = {
        str     = { 19, 20, 21, 22 },
        dexFix  = 9,
        acid    = { 50, 75, 90, 100 },
        spm     = { 15, 25, 35, 50 },
        crush   = { 10, 15, 20, 25 },
    },
}

state.cureToTidal = {
    ["SPPR103"] = "CBKWTH1",
    ["SPPR215"] = "CBKWTH2",
    ["SPPR315"] = "CBKWTH3",
    ["SPPR401"] = "CBKWTH4",
    ["SPPR502"] = "CBKWTH5",
    ["SPPR514"] = "CBKWTH6",
}
%CBK_ELM_EXTRA_CURES%

state.tidalToCure = {}
for k, v in pairs(state.cureToTidal) do
    state.tidalToCure[v] = k
end

state.spellElemCache = {}

function state.HasSpellState(sprite, st)
    if not sprite or not st or st < 0 then return false end
    if sprite._spellStates and sprite._spellStates[st] ~= nil then
        return sprite._spellStates[st] == true
    end
    if type(EEex_Sprite_GetSpellState) == "function" then
        return EEex_Sprite_GetSpellState(sprite, st) == true
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

function state.GetDruidLevel(sprite)
    if not sprite then return 1 end
    if sprite._druidLevel then return sprite._druidLevel end
    local ds = sprite.m_derivedStats
    local bs = sprite.m_baseStats
    local cls = (sprite.m_typeAI and sprite.m_typeAI.m_Class) or (bs and bs.m_class) or 11
    if cls == 16 then -- FIGHTER_DRUID: druid is level2
        local lv2 = (ds and ds.m_nLevel2) or (bs and bs.m_level2) or 1
        return lv2
    end
    local lv1 = (ds and ds.m_nLevel1) or (bs and bs.m_level1) or 1
    local lv2 = (ds and ds.m_nLevel2) or (bs and bs.m_level2) or 0
    return math.max(lv1, lv2)
end

function state.LevelToTier(lv)
    if lv >= 15 then return 4 end
    if lv >= 12 then return 3 end
    if lv >= 7  then return 2 end
    return 1
end

function state.GetMagicWeaponResref(sprite)
    if not sprite then return nil end
    if type(sprite._magicWeaponRes) == "string" then
        return sprite._magicWeaponRes:upper()
    end
    local eq = sprite.m_equipment
    if eq and eq.m_items and type(eq.m_items.get) == "function" then
        local item = eq.m_items:get(34) -- SLOT_MISC19 (conjured magical weapon slot)
        if item and item.pRes and item.pRes.resref then
            local r = item.pRes.resref:get()
            if type(r) == "string" and r ~= "" then
                return r:upper()
            end
        end
    end
    return nil
end

function state.GetActiveFormAndTier(sprite)
    if not sprite then return 0, 0 end
    local wres = state.GetMagicWeaponResref(sprite)
    if wres then
        local fStr, tStr = wres:match("^CBKEF([1-4])([1-4])$")
        if fStr and tStr then
            return tonumber(fStr), tonumber(tStr)
        end
    end
    local tier = state.LevelToTier(state.GetDruidLevel(sprite))
    if state.HasSpellState(sprite, state.stFire)  then return 1, tier end
    if state.HasSpellState(sprite, state.stWater) then return 2, tier end
    if state.HasSpellState(sprite, state.stAir)   then return 3, tier end
    if state.HasSpellState(sprite, state.stEarth) then return 4, tier end
    return 0, 0
end

local function maxFloor(cur, flr)
    cur = cur or 0
    if cur < flr then return flr end
    return cur
end

local function iterMemList(listObj, cb)
    if not listObj then return end
    if type(listObj) == "table" and #listObj > 0 then
        for _, entry in ipairs(listObj) do
            cb(entry)
        end
    elseif type(EEex_Utility_IterateCPtrList) == "function" then
        EEex_Utility_IterateCPtrList(listObj, cb)
    end
end

local function getEntryRes(entry)
    if not entry then return "" end
    local sid = entry.m_spellId
    if type(sid) == "string" then return sid:upper() end
    if sid and type(sid.get) == "function" then return (sid:get() or ""):upper() end
    return ""
end

local function setEntryRes(entry, newRes)
    if not entry then return end
    local sid = entry.m_spellId
    if type(sid) == "string" or sid == nil then
        entry.m_spellId = newRes
    elseif type(sid.set) == "function" then
        sid:set(newRes)
    end
end

-- Synchronizes remaining daily charges across CBKELF1..4 to their minimum ready count.
function state.SyncFormCharges(sprite)
    if not sprite then return end
    local memInnate = sprite.m_memorizedSpellsInnate
    if not memInnate then return end
    local innList = (type(memInnate.getReference) == "function") and memInnate:getReference(0) or memInnate[1] or memInnate
    if not innList then return end

    local byForm = { CBKELF1 = {}, CBKELF2 = {}, CBKELF3 = {}, CBKELF4 = {} }
    local presentCount = 0
    iterMemList(innList, function(entry)
        local r = getEntryRes(entry)
        if byForm[r] then
            table.insert(byForm[r], entry)
        end
    end)

    local minReady = nil
    for _, fname in ipairs(state.FORM_SHAPES) do
        local slots = byForm[fname]
        if #slots > 0 then
            presentCount = presentCount + 1
            local rdy = 0
            for _, e in ipairs(slots) do
                if bit.band(e.m_flags or 0, 1) ~= 0 then
                    rdy = rdy + 1
                end
            end
            if minReady == nil or rdy < minReady then
                minReady = rdy
            end
        end
    end

    if presentCount < 4 or minReady == nil then return end

    for _, fname in ipairs(state.FORM_SHAPES) do
        local slots = byForm[fname]
        local rdySeen = 0
        for _, e in ipairs(slots) do
            if bit.band(e.m_flags or 0, 1) ~= 0 then
                rdySeen = rdySeen + 1
                if rdySeen > minReady then
                    e.m_flags = bit.band(e.m_flags or 0, bit.bnot(1))
                end
            end
        end
    end
end

-- Swaps memorized Priest Cure Wounds <-> Tidal Healing CBKWTH1..6 while preserving m_flags.
function state.SyncTidalHealing(sprite, inWater)
    if not sprite then return 0 end
    local memPriest = sprite.m_memorizedSpellsPriest
    if not memPriest then return 0 end
    local map = inWater and state.cureToTidal or state.tidalToCure
    local swapped = 0
    for lvl = 0, 6 do
        local listObj = nil
        if type(memPriest.getReference) == "function" then
            listObj = memPriest:getReference(lvl)
        elseif type(memPriest) == "table" then
            listObj = memPriest[lvl + 1]
        end
        if listObj then
            iterMemList(listObj, function(entry)
                local r = getEntryRes(entry)
                local repl = map[r]
                if repl then
                    setEntryRes(entry, repl)
                    swapped = swapped + 1
                end
            end)
        end
    end
    return swapped
end

-- Applies non-downgrading STR/DEX floors (DEX=9 in Earth) and non-additive DR/Elemental floors.
function state.OnListsResolved(sprite)
    if not sprite then return false end
    local ds = sprite.m_derivedStats
    if not ds then return false end

    state.SyncFormCharges(sprite)

    local formIdx, tierIdx = state.GetActiveFormAndTier(sprite)
    state.SyncTidalHealing(sprite, formIdx == 2)

    if formIdx == 0 then return false end
    if state.stResolved >= 0 and state.HasSpellState(sprite, state.stResolved) then
        return false
    end

    local cfg = state.FORM_FLOORS[formIdx]
    if not cfg then return false end

    local strFloor = cfg.str[tierIdx]
    if strFloor and (ds.m_nSTR or 0) < strFloor then
        ds.m_nSTR = strFloor
        ds.m_nSTRExtra = 0
    end

    if cfg.dexFix ~= nil then
        ds.m_nDEX = cfg.dexFix
    elseif cfg.dex then
        local dexFloor = cfg.dex[tierIdx]
        if dexFloor and (ds.m_nDEX or 0) < dexFloor then
            ds.m_nDEX = dexFloor
        end
    end

    if cfg.fire then
        local fl = cfg.fire[tierIdx]
        ds.m_nResistFire = maxFloor(ds.m_nResistFire, fl)
        if ds.m_nResistMagicFire ~= nil then
            ds.m_nResistMagicFire = maxFloor(ds.m_nResistMagicFire, fl)
        end
    end
    if cfg.cold then
        local fl = cfg.cold[tierIdx]
        ds.m_nResistCold = maxFloor(ds.m_nResistCold, fl)
        if ds.m_nResistMagicCold ~= nil then
            ds.m_nResistMagicCold = maxFloor(ds.m_nResistMagicCold, fl)
        end
    end
    if cfg.elec then
        ds.m_nResistElectricity = maxFloor(ds.m_nResistElectricity, cfg.elec[tierIdx])
    end
    if cfg.acid then
        ds.m_nResistAcid = maxFloor(ds.m_nResistAcid, cfg.acid[tierIdx])
    end

    if formIdx == 4 then
        local spm = cfg.spm[tierIdx]
        local cr  = cfg.crush[tierIdx]
        ds.m_nResistSlashing = maxFloor(ds.m_nResistSlashing, spm)
        ds.m_nResistPiercing = maxFloor(ds.m_nResistPiercing, spm)
        ds.m_nResistMissile  = maxFloor(ds.m_nResistMissile,  spm)
        ds.m_nResistCrushing = maxFloor(ds.m_nResistCrushing, cr)
    else
        local ph = cfg.phys[tierIdx]
        ds.m_nResistSlashing = maxFloor(ds.m_nResistSlashing, ph)
        ds.m_nResistCrushing = maxFloor(ds.m_nResistCrushing, ph)
        ds.m_nResistPiercing = maxFloor(ds.m_nResistPiercing, ph)
        local ms = (cfg.missile and cfg.missile[tierIdx]) or ph
        ds.m_nResistMissile  = maxFloor(ds.m_nResistMissile,  ms)
    end

    if state.stResolved >= 0 then
        state.SetResolvedState(sprite, state.stResolved)
    end
    return true
end

function state.GetEffectSourceRes(effect)
    if not effect then return "" end
    local sr = effect.m_sourceRes
    if type(sr) == "string" then return sr:upper() end
    if sr and type(sr.get) == "function" then return (sr:get() or ""):upper() end
    return ""
end

function state.GetSpellElementMask(resref)
    if type(resref) ~= "string" or resref == "" then return 0 end
    local up = resref:upper()
    if state.spellElemCache[up] ~= nil then
        return state.spellElemCache[up]
    end
    local mask = 0
    if type(EEex_Resource_Demand) == "function" and type(EEex_Resource_GetSpellAbility) == "function"
        and type(EEex_UDToPtr) == "function" and type(EEex_ReadU16) == "function" and type(EEex_ReadU32) == "function" then
        local hdr = EEex_Resource_Demand(up, "SPL")
        if hdr and (hdr.abilityCount or 0) > 0 then
            local ab = EEex_Resource_GetSpellAbility(hdr, 0)
            if ab then
                local hdrPtr = EEex_UDToPtr(hdr)
                local fxOff = EEex_ReadU32(hdrPtr + 0x6A)
                local startIdx = ab.startingEffect or 0
                local cnt = ab.featureBlockCount or 0
                for i = 0, cnt - 1 do
                    local fPtr = hdrPtr + fxOff + (startIdx + i) * 0x30
                    local op = EEex_ReadU16(fPtr)
                    if op == 12 then
                        local p2 = EEex_ReadU32(fPtr + 0x08)
                        mask = bit.bor(mask, bit.band(p2, 0xFFFF0000))
                    end
                end
            end
        end
    end
    state.spellElemCache[up] = mask
    return mask
end

function state.EffectMatchesFormSpell(effect, formIdx)
    if not effect or formIdx < 1 or formIdx > 4 then return false end
    local sres = state.GetEffectSourceRes(effect)
    if sres:match("^CBKEF[1-4][1-4]$") then return false end
    local stype = effect.m_sourceType or 1
    if stype == 2 then return false end -- item source, not a spell
    local wantFlag = state.FORM_ELEM_FLAG[formIdx]
    if not wantFlag then return false end
    if effect.m_effectId == 12 then
        return bit.band(effect.m_dWFlags or 0, 0xFFFF0000) == wantFlag
    end
    if sres ~= "" then
        return bit.band(state.GetSpellElementMask(sres), wantFlag) ~= 0
    end
    return false
end

function state.GetSpriteRace(sprite)
    if not sprite then return 0 end
    if sprite._race then return sprite._race end
    if sprite.m_typeAI and sprite.m_typeAI.m_Race then return sprite.m_typeAI.m_Race end
    if sprite.m_baseStats and sprite.m_baseStats.m_race then return sprite.m_baseStats.m_race end
    return 0
end

-- Primal Penetration CheckSave listener: halves target MR for the Elementalist's own active-element spells.
function state.OnCheckSaveBefore(srcSprite, tgtSprite, effect, ctx)
    if not srcSprite or not tgtSprite or not effect or not ctx then return end
    if not state.HasSpellState(srcSprite, state.stHla) then return end
    local formIdx = state.GetActiveFormAndTier(srcSprite)
    if formIdx == 0 then return end
    if not state.EffectMatchesFormSpell(effect, formIdx) then return end

    local tds = tgtSprite.m_derivedStats
    if not tds or tds.m_nResistMagic == nil then return end
    local origMR = tds.m_nResistMagic
    if origMR > 0 then
        ctx.elmSavedMR = origMR
        tds.m_nResistMagic = math.floor(origMR / 2)
    end
end

function state.OnCheckSaveAfter(srcSprite, tgtSprite, effect, ctx)
    if ctx and ctx.elmSavedMR ~= nil and tgtSprite and tgtSprite.m_derivedStats then
        tgtSprite.m_derivedStats.m_nResistMagic = ctx.elmSavedMR
        ctx.elmSavedMR = nil
    end
end

-- Primal Penetration & Tectonic Strikes Damage listener:
-- 1. Caps non-ELEMENTAL target elemental res at <= 70% for the Elementalist's own active-element spells.
-- 2. In Earth Form, melee Crushing hits (CBKEF41..44) ignore 25% of target Crushing resistance.
function state.OnDamageBefore(srcSprite, tgtSprite, effect, ctx)
    if not srcSprite or not tgtSprite or not effect or not ctx then return end
    if not state.HasSpellState(srcSprite, state.stHla) then return end
    local formIdx = state.GetActiveFormAndTier(srcSprite)
    if formIdx == 0 then return end
    local tds = tgtSprite.m_derivedStats
    if not tds then return end

    local sres = state.GetEffectSourceRes(effect)
    local dmgHigh = bit.band(effect.m_dWFlags or 0, 0xFFFF0000)

    -- Earth Form Tectonic Strikes: melee Crushing hit from CBKEF41..44 ignores 25% Crushing resistance
    if formIdx == 4 and dmgHigh == state.DMG_CRUSHING and sres:match("^CBKEF4[1-4]$") then
        local curCrush = tds.m_nResistCrushing or 0
        if curCrush > 0 then
            ctx.elmSavedCrush = curCrush
            tds.m_nResistCrushing = math.max(0, curCrush - 25)
        end
        return
    end

    if state.GetSpriteRace(tgtSprite) == state.RACE_ELEMENTAL then return end
    if not state.EffectMatchesFormSpell(effect, formIdx) then return end

    if formIdx == 1 and dmgHigh == state.DMG_FIRE then
        if (tds.m_nResistFire or 0) > 70 then
            ctx.elmSavedFire = tds.m_nResistFire
            tds.m_nResistFire = 70
        end
        if tds.m_nResistMagicFire and tds.m_nResistMagicFire > 70 then
            ctx.elmSavedMFire = tds.m_nResistMagicFire
            tds.m_nResistMagicFire = 70
        end
    elseif formIdx == 2 and dmgHigh == state.DMG_COLD then
        if (tds.m_nResistCold or 0) > 70 then
            ctx.elmSavedCold = tds.m_nResistCold
            tds.m_nResistCold = 70
        end
        if tds.m_nResistMagicCold and tds.m_nResistMagicCold > 70 then
            ctx.elmSavedMCold = tds.m_nResistMagicCold
            tds.m_nResistMagicCold = 70
        end
    elseif formIdx == 3 and dmgHigh == state.DMG_ELEC then
        if (tds.m_nResistElectricity or 0) > 70 then
            ctx.elmSavedElec = tds.m_nResistElectricity
            tds.m_nResistElectricity = 70
        end
    elseif formIdx == 4 and dmgHigh == state.DMG_ACID then
        if (tds.m_nResistAcid or 0) > 70 then
            ctx.elmSavedAcid = tds.m_nResistAcid
            tds.m_nResistAcid = 70
        end
    end
end

function state.OnDamageAfter(srcSprite, tgtSprite, effect, ctx)
    if not ctx or not tgtSprite or not tgtSprite.m_derivedStats then return end
    local tds = tgtSprite.m_derivedStats
    if ctx.elmSavedCrush ~= nil then tds.m_nResistCrushing    = ctx.elmSavedCrush; ctx.elmSavedCrush = nil end
    if ctx.elmSavedFire  ~= nil then tds.m_nResistFire        = ctx.elmSavedFire;  ctx.elmSavedFire  = nil end
    if ctx.elmSavedMFire ~= nil then tds.m_nResistMagicFire   = ctx.elmSavedMFire; ctx.elmSavedMFire = nil end
    if ctx.elmSavedCold  ~= nil then tds.m_nResistCold        = ctx.elmSavedCold;  ctx.elmSavedCold  = nil end
    if ctx.elmSavedMCold ~= nil then tds.m_nResistMagicCold   = ctx.elmSavedMCold; ctx.elmSavedMCold = nil end
    if ctx.elmSavedElec  ~= nil then tds.m_nResistElectricity = ctx.elmSavedElec;  ctx.elmSavedElec  = nil end
    if ctx.elmSavedAcid  ~= nil then tds.m_nResistAcid        = ctx.elmSavedAcid;  ctx.elmSavedAcid  = nil end
end

if not state.listenersRegistered then
    state.listenersRegistered = true

    if EEex_Opcode_AddListsResolvedListener then
        EEex_Opcode_AddListsResolvedListener(function(sprite)
            pcall(state.OnListsResolved, sprite)
        end)
    end

    if EEex_Sprite_AddQuickListsCheckedListener then
        EEex_Sprite_AddQuickListsCheckedListener(function(sprite)
            pcall(state.SyncFormCharges, sprite)
        end)
    end

    if CBKCombat and type(CBKCombat.AddCheckSaveListener) == "function" then
        local csStack = {}
        local function resolveSource(eff, explicitSrc)
            if explicitSrc then return explicitSrc end
            if eff and eff._sourceSprite then return eff._sourceSprite end
            if eff and eff.m_sourceId and type(EEex_GameObject_Get) == "function" then
                local ok, sp = pcall(EEex_GameObject_Get, eff.m_sourceId)
                if ok then return sp end
            end
            return nil
        end
        CBKCombat.AddCheckSaveListener(
            function(eff, tgt)
                local ctx = {}
                local src = resolveSource(eff, nil)
                csStack[#csStack + 1] = { src = src, tgt = tgt, eff = eff, ctx = ctx }
                state.OnCheckSaveBefore(src, tgt, eff, ctx)
            end,
            function(_eff, tgt)
                local frame = csStack[#csStack]
                csStack[#csStack] = nil
                if frame then
                    state.OnCheckSaveAfter(frame.src, tgt or frame.tgt, frame.eff, frame.ctx)
                end
            end
        )
    end

    if CBKCombat and type(CBKCombat.AddDamageListener) == "function" then
        local dmgStack = {}
        local function resolveSource(eff, explicitSrc)
            if explicitSrc then return explicitSrc end
            if eff and eff._sourceSprite then return eff._sourceSprite end
            if eff and eff.m_sourceId and type(EEex_GameObject_Get) == "function" then
                local ok, sp = pcall(EEex_GameObject_Get, eff.m_sourceId)
                if ok then return sp end
            end
            return nil
        end
        CBKCombat.AddDamageListener(
            function(eff, src, tgt)
                local ctx = {}
                local rsrc = resolveSource(eff, src)
                dmgStack[#dmgStack + 1] = { src = rsrc, tgt = tgt, eff = eff, ctx = ctx }
                state.OnDamageBefore(rsrc, tgt, eff, ctx)
            end,
            function(_eff, _src, tgt)
                local frame = dmgStack[#dmgStack]
                dmgStack[#dmgStack] = nil
                if frame then
                    state.OnDamageAfter(frame.src, tgt or frame.tgt, frame.eff, frame.ctx)
                end
            end
        )
    end
end
