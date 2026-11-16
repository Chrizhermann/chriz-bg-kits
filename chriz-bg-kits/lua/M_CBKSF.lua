-- M_CBKSF.lua: Stonefire Sorcerer (Component 210)
-- 1. Filters Illusion-school spells (SCHOOL.IDS = 5) out of Sorcerer spell selection
--    (CHARGEN_CHOOSE_SPELLS on both character creation and level-up).
-- 2. Restores CBK_STONEFIRE_ARMOR spell state in m_derivedStats.m_spellStates on save load
--    before CGameSpriteEquipment::Unmarshal equips armor, so equipped op318 guards never
--    fail at load time.

CBKStonefire = CBKStonefire or {}
local state = CBKStonefire

state.kitIds = tonumber("%CBK_STONEFIRE_KIT_IDS%") or -1
state.armorState = tonumber("%CBK_STONEFIRE_ARMOR_STATE%") or -1
state.ILLUSION_SCHOOL = 5

function state.GetSpriteKitIds(sprite)
    if not sprite then return 0 end
    local bs = sprite.m_baseStats
    if bs and bs.m_mageSpecUpperWord ~= nil and bs.m_mageSpecialization ~= nil then
        local hi = bit.band(bs.m_mageSpecUpperWord, 0xFFFF)
        local lo = bit.band(bs.m_mageSpecialization, 0xFFFF)
        return bit.bor(bit.lshift(hi, 16), lo)
    end
    if type(EEex_Sprite_GetStat) == "function" then
        return EEex_Sprite_GetStat(sprite, 152) or 0
    end
    return 0
end

function state.GetSpellSchool(resref)
    if type(resref) ~= "string" or resref == "" then return 0 end
    if state.mockSpellSchools and state.mockSpellSchools[resref:upper()] ~= nil then
        return state.mockSpellSchools[resref:upper()]
    end
    if type(EEex_Resource_Demand) == "function" then
        local hdr = EEex_Resource_Demand(resref, "SPL")
        if hdr then
            if hdr.primaryType ~= nil then return hdr.primaryType end
            if hdr.school ~= nil then return hdr.school end
        end
    end
    return 0
end

-- Disables Illusion-school spells in chargen.choose_spell for Stonefire Sorcerers.
function state.FilterChooseSpells(chooseList, kitIds)
    if type(chooseList) ~= "table" then return 0 end
    if kitIds ~= state.kitIds or state.kitIds < 0 then return 0 end
    local firstEntry = chooseList[1]
    if firstEntry and type(firstEntry.key) == "string" then
        local prefix = firstEntry.key:upper():sub(1, 4)
        if prefix == "SPPR" then return 0 end
    end
    local disabled = 0
    for _, entry in ipairs(chooseList) do
        if type(entry) == "table" and type(entry.key) == "string" then
            if state.GetSpellSchool(entry.key) == state.ILLUSION_SCHOOL then
                entry.enabled = false
                disabled = disabled + 1
            end
        end
    end
    return disabled
end

function state.OnSpriteLoaded(sprite)
    if not sprite or state.armorState < 0 or state.armorState > 255 then return false end
    if type(EEex_Utility_IterateCPtrList) ~= "function" then return false end
    local mark = state.armorState
    local found = false
    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, function(effect)
        local timing = effect.m_durationType
        if effect.m_effectId == 328 and effect.m_special ~= 0 and effect.m_dWFlags == mark
            and (timing < 3 or timing > 8) then
            found = true
            return true
        end
    end)
    if not found then return false end
    local ds = sprite.m_derivedStats
    if ds and ds.m_spellStates then
        local word = math.floor(mark / 32)
        local mask = (type(EEex_LShift) == "function") and EEex_LShift(1, mark % 32) or bit.lshift(1, mark % 32)
        local borFn = (type(EEex_BOr) == "function") and EEex_BOr or bit.bor
        ds.m_spellStates:set(word, borFn(ds.m_spellStates:get(word), mask))
        return true
    end
    return false
end

if not state.listenersRegistered then
    state.listenersRegistered = true

    if EEex_Sprite_AddLoadedListener then
        EEex_Sprite_AddLoadedListener(function(sprite)
            pcall(state.OnSpriteLoaded, sprite)
        end)
    end

    if EEex_Menu_AddAfterMainFileLoadedListener then
        EEex_Menu_AddAfterMainFileLoadedListener(function()
            if type(EEex_Menu_Find) ~= "function" then return end
            local menu = EEex_Menu_Find("CHARGEN_CHOOSE_SPELLS")
            if not menu or state.chooseWrapped then return end
            state.chooseWrapped = true
            local function runSpellFilter()
                if not chargen or type(chargen.choose_spell) ~= "table" then return end
                local sp = (type(EEex_GameObject_Get) == "function" and currentID) and EEex_GameObject_Get(currentID) or nil
                local kitIds = state.GetSpriteKitIds(sp)
                if (kitIds == 0 or kitIds == 0x4000) and chargen.kit and type(chargen.kit) == "table" and currentChargenKit then
                    local selKit = chargen.kit[currentChargenKit]
                    if selKit and selKit.id then
                        kitIds = 0x4000 + selKit.id
                    end
                end
                state.FilterChooseSpells(chargen.choose_spell, kitIds)
            end
            if type(EEex_Menu_GetItemFunction) == "function" and type(EEex_Menu_SetItemFunction) == "function"
                and menu.reference_onOpen ~= nil and type(menu.reference_onOpen) ~= "function" then
                local origOnOpen = EEex_Menu_GetItemFunction(menu.reference_onOpen)
                EEex_Menu_SetItemFunction(menu.reference_onOpen, function(...)
                    if origOnOpen then origOnOpen(...) end
                    runSpellFilter()
                end)
            else
                local origOnOpen = menu.reference_onOpen
                menu.reference_onOpen = function(...)
                    if origOnOpen then origOnOpen(...) end
                    runSpellFilter()
                end
            end
        end)
    end
end
