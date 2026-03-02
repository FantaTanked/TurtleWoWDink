-- TurtleDink v2.0.0
-- Shows an in-game chat message on level-up.
-- Discord notifications are handled automatically by the GitHub-hosted service.

local CHAT_PREFIX = "|cff00ccff[TurtleDink]|r "

local TurtleDinkDB = TurtleDinkDB or {}

local function InitDB()
    TurtleDinkDB.enabled = TurtleDinkDB.enabled ~= false  -- default true
end

local function Print(msg)
    DEFAULT_CHAT_FRAME:AddMessage(CHAT_PREFIX .. msg)
end

local function OnLevelUp(newLevel)
    if not TurtleDinkDB.enabled then return end

    local playerName = UnitName("player")
    local className  = UnitClass("player")
    local raceName   = UnitRace("player")

    Print(
        "|cffFFD700" .. playerName .. "|r" ..
        " reached level |cffFFD700" .. newLevel .. "|r!" ..
        " |cffaaaaaa(" .. (raceName or "?") .. " " .. (className or "?") .. ")|r"
    )
    Print("|cff00ff00Discord notification will be sent automatically.|r")
end

-- ---------------------------------------------------------------------------
-- Slash commands
-- ---------------------------------------------------------------------------
local function HandleSlashCommand(msg)
    local cmd = string.lower(msg or "")

    if cmd == "" or cmd == "help" then
        Print("Commands:")
        Print("  |cffffffff/tdink enable|r  - Enable in-game messages")
        Print("  |cffffffff/tdink disable|r - Disable in-game messages")
        Print("  |cffffffff/tdink status|r  - Show current status")

    elseif cmd == "enable" then
        TurtleDinkDB.enabled = true
        Print("|cff00ff00In-game messages enabled.|r")

    elseif cmd == "disable" then
        TurtleDinkDB.enabled = false
        Print("|cffff0000In-game messages disabled.|r")

    elseif cmd == "status" then
        local state = TurtleDinkDB.enabled and "|cff00ff00enabled|r" or "|cffff0000disabled|r"
        Print("In-game messages: " .. state)

    else
        Print("Unknown command: |cffffffff" .. msg .. "|r  —  try |cffffffff/tdink help|r")
    end
end

-- ---------------------------------------------------------------------------
-- Event frame
-- ---------------------------------------------------------------------------
local frame = CreateFrame("Frame", "TurtleDinkFrame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_LEVEL_UP")

frame:SetScript("OnEvent", function()
    if event == "PLAYER_LOGIN" then
        InitDB()
        Print("Loaded. Type |cffffffff/tdink help|r for commands.")

    elseif event == "PLAYER_LEVEL_UP" then
        local newLevel = arg1 or UnitLevel("player")
        OnLevelUp(newLevel)
    end
end)

SLASH_TDINK1 = "/tdink"
SLASH_TDINK2 = "/turtledink"
SlashCmdList["TDINK"] = HandleSlashCommand
