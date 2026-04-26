--[[
==============================================================
     AUTO LIP SYNC v4.1 -- Roblox Plugin for Moon Animator 2
     Simple text config with fixed UI
==============================================================

NEW IN v4.1:
+ Simple text config -- paste and apply!
+ Fixed UI -- elements no longer overlap
+ Automatic container height calculation
+ One-click config apply
+ FIXED: volume fallback (Lua "" is truthy -- now checked explicitly)

CONFIG FORMAT:
CLOSED: 6550795382
A,E,I quiet: 2840140471
A,E,I loud: 6107690672
O,U quiet: 5998754410
O,U loud: 5921729062
M: 6550795382
F,S,L,T quiet: 2840140471
F,S,L,T loud: 6107690672

NOTE: The Python analyzer does NOT produce the "TH" viseme --
  it is excluded from the config. Add "TH" to the F,S,L,T line
  if you ever need it.
--]]

local HttpService = game:GetService("HttpService")
local Selection   = game:GetService("Selection")

if not plugin then
	warn("[AutoLipSync v4.1] Must run as Plugin!")
	return
end

-- ==============================================================
-- VISEME TABLE
-- Note: "TH" removed -- Python analyzer never emits it.
-- ==============================================================
local VISEME_NAMES = {
	"CLOSED", "A", "E", "I", "O", "U",
	"M", "F", "S", "L", "T",
}

local VOLUME_LEVELS = {"quiet", "normal", "loud"}

-- ==============================================================
-- COLORS
-- ==============================================================
local C = {
	BG      = Color3.fromRGB(28, 28, 35),
	PANEL   = Color3.fromRGB(38, 38, 48),
	ACCENT  = Color3.fromRGB(100, 180, 255),
	GREEN   = Color3.fromRGB(80, 210, 120),
	RED     = Color3.fromRGB(255, 90, 90),
	YELLOW  = Color3.fromRGB(255, 200, 50),
	ORANGE  = Color3.fromRGB(255, 154, 60),
	TEXT    = Color3.fromRGB(230, 230, 230),
	DIMTEXT = Color3.fromRGB(150, 150, 165),
	BTN     = Color3.fromRGB(55, 55, 75),
}

-- ==============================================================
-- STATE
-- ==============================================================
local state = {
	jsonData       = nil,
	selectedFolder = nil,
	fps            = 24,
	mode           = "simple",
	simpleMap      = {},
	volumeMap      = {},
}

for _, v in ipairs(VISEME_NAMES) do
	state.simpleMap[v] = ""
	state.volumeMap[v] = {quiet = "", normal = "", loud = ""}
end

-- ==============================================================
-- FIX: safe texture picker
-- In Lua, empty string "" is truthy, so "a or b" returns ""
-- if a == "". This function explicitly checks for a non-empty value.
-- ==============================================================
local function pickTexture(...)
	for _, v in ipairs({...}) do
		if type(v) == "string" and v ~= "" then
			return v
		end
	end
	return nil
end

-- ==============================================================
-- CONFIG PARSER
-- ==============================================================
local function parseConfig(configText)
	local success = 0
	local errors  = {}

	for line in configText:gmatch("[^\r\n]+") do
		line = line:gsub("^%s+", ""):gsub("%s+$", "")
		if line ~= "" and not line:match("^#") and not line:match("^//") then
			local phonemes, level, assetId = line:match("([A-Z,]+)%s*(%w*)%s*:%s*(%d+)")

			if phonemes and assetId then
				level   = level:lower()
				assetId = "rbxassetid://" .. assetId

				for ph in phonemes:gmatch("[A-Z]+") do
					if state.volumeMap[ph] then
						if level == "" or level == "all" then
							state.volumeMap[ph].quiet  = assetId
							state.volumeMap[ph].normal = assetId
							state.volumeMap[ph].loud   = assetId
							state.simpleMap[ph]        = assetId
						elseif level == "quiet" or level == "normal" or level == "loud" then
							state.volumeMap[ph][level] = assetId
							if level == "normal" then
								state.simpleMap[ph] = assetId
							elseif state.simpleMap[ph] == "" then
								state.simpleMap[ph] = assetId
							end
						end
						success = success + 1
					else
						table.insert(errors, "Unknown phoneme: " .. ph)
					end
				end
			else
				table.insert(errors, "Invalid format: " .. line)
			end
		end
	end

	return success, errors
end

-- ==============================================================
-- CORE: CREATE KEYFRAMES
-- ==============================================================
local function createKeyframe(textureFolder, frameNum, assetId)
	local frameFolder = textureFolder:FindFirstChild(tostring(frameNum))
	if not frameFolder or frameFolder.ClassName ~= "Folder" then
		frameFolder        = Instance.new("Folder")
		frameFolder.Name   = tostring(frameNum)
		frameFolder.Parent = textureFolder
	end

	local valuesFolder = frameFolder:FindFirstChild("Values")
	if not valuesFolder or valuesFolder.ClassName ~= "Folder" then
		valuesFolder        = Instance.new("Folder")
		valuesFolder.Name   = "Values"
		valuesFolder.Parent = frameFolder
	end

	local valueSV = valuesFolder:FindFirstChild("0")
	if not valueSV or valueSV.ClassName ~= "StringValue" then
		valueSV        = Instance.new("StringValue")
		valueSV.Name   = "0"
		valueSV.Parent = valuesFolder
	end
	valueSV.Value = assetId

	local easesFolder = frameFolder:FindFirstChild("Eases")
	if not easesFolder or easesFolder.ClassName ~= "Folder" then
		easesFolder        = Instance.new("Folder")
		easesFolder.Name   = "Eases"
		easesFolder.Parent = frameFolder
	end

	local ease0Folder = easesFolder:FindFirstChild("0")
	if not ease0Folder or ease0Folder.ClassName ~= "Folder" then
		ease0Folder        = Instance.new("Folder")
		ease0Folder.Name   = "0"
		ease0Folder.Parent = easesFolder
	end

	local typeSV = ease0Folder:FindFirstChild("Type")
	if not typeSV or typeSV.ClassName ~= "StringValue" then
		typeSV        = Instance.new("StringValue")
		typeSV.Name   = "Type"
		typeSV.Parent = ease0Folder
	end
	typeSV.Value = "Constant"
end

-- ==============================================================
-- APPLY LIP SYNC
-- ==============================================================
local function applyLipSync()
	if not state.jsonData then
		return false, "JSON not loaded!"
	end
	if not state.selectedFolder then
		return false, "Select a face folder in Explorer!"
	end

	local keyframes = state.jsonData.keyframes
	local fps = (state.jsonData.meta and state.jsonData.meta.fps) or state.fps

	if not keyframes or #keyframes == 0 then
		return false, "No keyframes found in JSON!"
	end

	local hasTextures = false
	if state.mode == "simple" then
		for _, tex in pairs(state.simpleMap) do
			if tex ~= "" then hasTextures = true; break end
		end
	else
		for _, volMap in pairs(state.volumeMap) do
			for _, tex in pairs(volMap) do
				if tex ~= "" then hasTextures = true; break end
			end
			if hasTextures then break end
		end
	end

	if not hasTextures then
		return false, "Fill at least one texture or apply the config!"
	end

	local textureFolder = state.selectedFolder:FindFirstChild("Texture")
	if not textureFolder or textureFolder.ClassName ~= "Folder" then
		textureFolder        = Instance.new("Folder")
		textureFolder.Name   = "Texture"
		textureFolder.Parent = state.selectedFolder
	end

	local count      = 0
	local volumeUsed = {quiet = 0, normal = 0, loud = 0}

	for _, kf in ipairs(keyframes) do
		local viseme = kf.viseme  or "CLOSED"
		local frame  = kf.frame   or math.floor((kf.time_sec or 0) * fps)
		local volume = kf.volume  or "normal"

		local texId = nil

		if state.mode == "simple" then
			texId = pickTexture(
				state.simpleMap[viseme],
				state.simpleMap["CLOSED"]
			)
		else
			local volMap = state.volumeMap[viseme]
			if volMap then
				texId = pickTexture(
					volMap[volume],
					volMap["normal"],
					volMap["quiet"],
					volMap["loud"]
				)
			end
			if not texId then
				local closedMap = state.volumeMap["CLOSED"]
				if closedMap then
					texId = pickTexture(
						closedMap[volume],
						closedMap["normal"],
						closedMap["quiet"],
						closedMap["loud"]
					)
				end
			end
		end

		if texId then
			createKeyframe(textureFolder, frame, texId)
			count = count + 1
			volumeUsed[volume] = (volumeUsed[volume] or 0) + 1
		end
	end

	if count == 0 then
		return false, "No keyframes created! Check your config (re-apply it)."
	end

	local result = string.format(
		"Success! Created %d keyframes\n\n"
			.. "Path: %s/Texture\n"
			.. "FPS: %d | Language: %s\n",
		count,
		state.selectedFolder:GetFullName(),
		fps,
		(state.jsonData.meta and state.jsonData.meta.language) or "?"
	)

	if state.mode == "volume" then
		result = result .. string.format(
			"\nVolume: quiet=%d normal=%d loud=%d\n",
			volumeUsed.quiet  or 0,
			volumeUsed.normal or 0,
			volumeUsed.loud   or 0
		)
	end

	result = result .. "\nOpen Moon Animator 2 -> File -> Open"
	return true, result
end

-- ==============================================================
-- UI HELPERS
-- ==============================================================
local function makeFrame(parent, props)
	local f = Instance.new("Frame")
	f.BackgroundColor3 = props.bg   or C.BG
	f.BorderSizePixel  = 0
	f.Size             = props.size or UDim2.new(1, 0, 0, 30)
	f.Position         = props.pos  or UDim2.new(0, 0, 0, 0)
	f.LayoutOrder      = props.order or 0
	f.Parent           = parent
	if props.autosize then
		f.AutomaticSize = Enum.AutomaticSize.Y
	end
	return f
end

local function makeLabel(parent, text, props)
	props = props or {}
	local l = Instance.new("TextLabel")
	l.Text             = text
	l.Font             = props.font  or Enum.Font.GothamMedium
	l.TextSize         = props.size  or 13
	l.TextColor3       = props.color or C.TEXT
	l.BackgroundTransparency = 1
	l.TextXAlignment   = props.align or Enum.TextXAlignment.Left
	l.TextWrapped      = true
	l.Size             = props.sz    or UDim2.new(1, 0, 0, 20)
	l.LayoutOrder      = props.order or 0
	l.Parent           = parent
	if props.autosize then
		l.AutomaticSize = Enum.AutomaticSize.Y
	end
	return l
end

local function makeButton(parent, text, props)
	props = props or {}
	local b = Instance.new("TextButton")
	b.Text              = text
	b.Font              = props.font  or Enum.Font.GothamBold
	b.TextSize          = props.tsize or 13
	b.TextColor3        = props.tc    or C.BG
	b.BackgroundColor3  = props.bg    or C.ACCENT
	b.BorderSizePixel   = 0
	b.Size              = props.size  or UDim2.new(1, 0, 0, 34)
	b.LayoutOrder       = props.order or 0
	b.AutoButtonColor   = true
	b.Parent            = parent
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 6)
	corner.Parent = b
	return b
end

local function makeTextBox(parent, placeholder, props)
	props = props or {}
	local tb = Instance.new("TextBox")
	tb.PlaceholderText   = placeholder
	tb.PlaceholderColor3 = C.DIMTEXT
	tb.Text              = props.text  or ""
	tb.Font              = props.font  or Enum.Font.Gotham
	tb.TextSize          = props.tsize or 12
	tb.TextColor3        = C.TEXT
	tb.BackgroundColor3  = C.PANEL
	tb.BorderSizePixel   = 1
	tb.BorderColor3      = Color3.fromRGB(60, 60, 75)
	tb.Size              = props.size  or UDim2.new(1, 0, 0, 28)
	tb.LayoutOrder       = props.order or 0
	tb.TextXAlignment    = Enum.TextXAlignment.Left
	tb.MultiLine         = props.multi or false
	tb.ClearTextOnFocus  = false
	tb.ClipsDescendants  = true
	tb.Parent            = parent
	local pad = Instance.new("UIPadding")
	pad.PaddingLeft = UDim.new(0, 8)
	pad.Parent = tb
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 5)
	corner.Parent = tb
	return tb
end

local function makeSep(parent, title, order)
	local f   = makeFrame(parent, {bg = C.BG, size = UDim2.new(1, -16, 0, 28), order = order})
	local _ln = makeFrame(f, {bg = Color3.fromRGB(60, 60, 75),
		size = UDim2.new(1, 0, 0, 1),
		pos  = UDim2.new(0, 0, 0, 10)})
	local lbl = makeLabel(f, " " .. title .. " ", {
		color    = C.ACCENT,
		size     = 11,
		font     = Enum.Font.GothamBold,
		sz       = UDim2.new(0, 320, 0, 20),
	})
	lbl.Position            = UDim2.new(0, 6, 0, 0)
	lbl.BackgroundColor3    = C.BG
	lbl.BackgroundTransparency = 0
	lbl.ZIndex              = 3
	return f
end

-- ==============================================================
-- BUILD UI
-- ==============================================================
local toolbar = plugin:CreateToolbar("Auto LipSync")
local button  = toolbar:CreateButton(
	"LipSync v4.1",
	"Auto LipSync v4.1 with text config",
	"rbxassetid://98951692122632"
)

local widgetInfo = DockWidgetPluginGuiInfo.new(
	Enum.InitialDockState.Right,
	false, false,
	420, 750,
	380, 600
)
local widget = plugin:CreateDockWidgetPluginGui("AutoLipSync_v41", widgetInfo)
widget.Title          = "Auto LipSync v4.1"
widget.ZIndexBehavior = Enum.ZIndexBehavior.Sibling

button.Click:Connect(function()
	widget.Enabled = not widget.Enabled
end)

local root = makeFrame(widget, {bg = C.BG, size = UDim2.new(1, 0, 1, 0)})

local scroll = Instance.new("ScrollingFrame")
scroll.Size                = UDim2.new(1, 0, 1, 0)
scroll.CanvasSize          = UDim2.new(0, 0, 0, 0)
scroll.AutomaticCanvasSize = Enum.AutomaticSize.Y
scroll.ScrollBarThickness  = 6
scroll.BackgroundColor3    = C.BG
scroll.BorderSizePixel     = 0
scroll.Parent              = root

local layout = Instance.new("UIListLayout")
layout.SortOrder = Enum.SortOrder.LayoutOrder
layout.Padding   = UDim.new(0, 4)
layout.Parent    = scroll

local pad = Instance.new("UIPadding")
pad.PaddingLeft   = UDim.new(0, 8)
pad.PaddingRight  = UDim.new(0, 8)
pad.PaddingTop    = UDim.new(0, 8)
pad.PaddingBottom = UDim.new(0, 12)
pad.Parent        = scroll

-- Header
local header = makeFrame(scroll, {bg = Color3.fromRGB(18, 18, 28),
	size = UDim2.new(1, 0, 0, 80), order = 1, autosize = true})
do
	local hlay = Instance.new("UIListLayout")
	hlay.SortOrder = Enum.SortOrder.LayoutOrder
	hlay.Parent    = header
	local hpad = Instance.new("UIPadding")
	hpad.PaddingTop    = UDim.new(0, 8)
	hpad.PaddingBottom = UDim.new(0, 8)
	hpad.Parent        = header
	makeLabel(header, "AUTO LIP SYNC v4.1", {
		color = C.ACCENT, size = 14, font = Enum.Font.GothamBold,
		sz = UDim2.new(1, 0, 0, 24), order = 1
	})
	makeLabel(header, "Texture-based lip sync for Moon Animator 2", {
		color = C.GREEN, size = 11,
		sz = UDim2.new(1, 0, 0, 18), order = 2
	})
	makeLabel(header, "Paste config -> Apply -> Done!", {
		color = C.DIMTEXT, size = 10,
		sz = UDim2.new(1, 0, 0, 18), order = 3
	})
end

-- Step 1: JSON
makeSep(scroll, "1. Paste JSON from Python", 10)
local jsonPanel = makeFrame(scroll, {bg = C.PANEL, size = UDim2.new(1, 0, 0, 120), order = 11, autosize = true})
do
	local jsonPad = Instance.new("UIPadding")
	jsonPad.PaddingLeft   = UDim.new(0, 8)
	jsonPad.PaddingRight  = UDim.new(0, 8)
	jsonPad.PaddingTop    = UDim.new(0, 8)
	jsonPad.PaddingBottom = UDim.new(0, 8)
	jsonPad.Parent        = jsonPanel
	local jsonLay = Instance.new("UIListLayout")
	jsonLay.Padding    = UDim.new(0, 4)
	jsonLay.SortOrder  = Enum.SortOrder.LayoutOrder
	jsonLay.Parent     = jsonPanel
end

local jsonBox = makeTextBox(jsonPanel, "Paste JSON here...", {
	size = UDim2.new(1, 0, 0, 90), multi = true, font = Enum.Font.Code, tsize = 10, order = 1
})

local jsonBtnRow = makeFrame(jsonPanel, {bg = C.PANEL, size = UDim2.new(1, 0, 0, 28), order = 2})
do
	local jsonBtnLay = Instance.new("UIListLayout")
	jsonBtnLay.FillDirection = Enum.FillDirection.Horizontal
	jsonBtnLay.Padding       = UDim.new(0, 6)
	jsonBtnLay.Parent        = jsonBtnRow
end
local loadJsonBtn  = makeButton(jsonBtnRow, "Load JSON",
	{size = UDim2.new(0.48, 0, 1, 0), bg = C.ACCENT})
loadJsonBtn.LayoutOrder = 1
local clearJsonBtn = makeButton(jsonBtnRow, "Clear",
	{size = UDim2.new(0.48, 0, 1, 0), bg = C.BTN, tc = C.TEXT})
clearJsonBtn.LayoutOrder = 2

local jsonStatus = makeLabel(scroll, "JSON: not loaded", {
	color = C.DIMTEXT, size = 11, order = 12, sz = UDim2.new(1, 0, 0, 16)
})

-- Step 2: Folder selection
makeSep(scroll, "2. Select face folder", 20)
local folderPanel = makeFrame(scroll, {bg = C.PANEL, size = UDim2.new(1, 0, 0, 90), order = 21, autosize = true})
do
	local folderPad = Instance.new("UIPadding")
	folderPad.PaddingLeft   = UDim.new(0, 8)
	folderPad.PaddingRight  = UDim.new(0, 8)
	folderPad.PaddingTop    = UDim.new(0, 8)
	folderPad.PaddingBottom = UDim.new(0, 8)
	folderPad.Parent        = folderPanel
	local folderLay = Instance.new("UIListLayout")
	folderLay.Padding   = UDim.new(0, 4)
	folderLay.SortOrder = Enum.SortOrder.LayoutOrder
	folderLay.Parent    = folderPanel
	makeLabel(folderPanel, "ServerStorage/MoonAnimator2Saves/[AnimName]/[N]", {
		color = C.YELLOW, size = 10, font = Enum.Font.Code,
		sz = UDim2.new(1, 0, 0, 14), order = 1, autosize = true
	})
	makeLabel(folderPanel, "Where [N] is the face folder number (e.g. \"2\")", {
		color = C.DIMTEXT, size = 10,
		sz = UDim2.new(1, 0, 0, 20), order = 2, autosize = true
	})
end
local pickFolderBtn = makeButton(folderPanel, "Use Selected",
	{size = UDim2.new(1, 0, 0, 28), bg = C.BTN, tc = C.TEXT, order = 3})
pickFolderBtn.Parent = folderPanel

local folderStatus = makeLabel(scroll, "Folder: not selected", {
	color = C.DIMTEXT, size = 11, order = 22, sz = UDim2.new(1, 0, 0, 16)
})

-- Step 3: Text config
makeSep(scroll, "3. Texture config", 30)
local configPanel = makeFrame(scroll, {bg = C.PANEL, size = UDim2.new(1, 0, 0, 200), order = 31, autosize = true})
do
	local configPad = Instance.new("UIPadding")
	configPad.PaddingLeft   = UDim.new(0, 8)
	configPad.PaddingRight  = UDim.new(0, 8)
	configPad.PaddingTop    = UDim.new(0, 8)
	configPad.PaddingBottom = UDim.new(0, 8)
	configPad.Parent        = configPanel
	local configLay = Instance.new("UIListLayout")
	configLay.Padding   = UDim.new(0, 4)
	configLay.SortOrder = Enum.SortOrder.LayoutOrder
	configLay.Parent    = configPanel
	makeLabel(configPanel, "Config format (TH excluded -- Python never emits it):", {
		color = C.ACCENT, size = 11, font = Enum.Font.GothamBold,
		sz = UDim2.new(1, 0, 0, 18), order = 1, autosize = true
	})
end

local exampleText = [[CLOSED: 6550795382
A,E,I quiet: 2840140471
A,E,I loud: 6107690672
O,U quiet: 5998754410
O,U loud: 5921729062
M: 6550795382
F,S,L,T quiet: 2840140471
F,S,L,T loud: 6107690672]]

makeLabel(configPanel, exampleText, {
	color = C.YELLOW, size = 9, font = Enum.Font.Code,
	sz = UDim2.new(1, 0, 0, 100), order = 2, autosize = true
})

makeLabel(configPanel, "Config is pre-filled below. Just click Apply Config:", {
	color = C.GREEN, size = 10,
	sz = UDim2.new(1, 0, 0, 20), order = 3, autosize = true
})

local configBox = makeTextBox(configPanel, "Config...", {
	size = UDim2.new(1, 0, 0, 120), multi = true, font = Enum.Font.Code, tsize = 10, order = 4,
	text = exampleText
})

local configBtnRow = makeFrame(configPanel, {bg = C.PANEL, size = UDim2.new(1, 0, 0, 28), order = 5})
do
	local configBtnLay = Instance.new("UIListLayout")
	configBtnLay.FillDirection = Enum.FillDirection.Horizontal
	configBtnLay.Padding       = UDim.new(0, 6)
	configBtnLay.Parent        = configBtnRow
end

local applyConfigBtn = makeButton(configBtnRow, "Apply Config",
	{size = UDim2.new(0.65, 0, 1, 0), bg = C.GREEN, tc = C.BG})
applyConfigBtn.LayoutOrder = 1

local clearConfigBtn = makeButton(configBtnRow, "Clear",
	{size = UDim2.new(0.33, 0, 1, 0), bg = C.BTN, tc = C.TEXT})
clearConfigBtn.LayoutOrder = 2

local configStatus = makeLabel(configPanel, "Config: ready to apply!", {
	color = C.GREEN, size = 10, sz = UDim2.new(1, 0, 0, 16), order = 6, autosize = true
})

-- Step 4: Mode
makeSep(scroll, "4. Mode (optional)", 40)
local modePanel = makeFrame(scroll, {bg = C.PANEL, size = UDim2.new(1, 0, 0, 70), order = 41, autosize = true})
do
	local modePad = Instance.new("UIPadding")
	modePad.PaddingLeft   = UDim.new(0, 8)
	modePad.PaddingRight  = UDim.new(0, 8)
	modePad.PaddingTop    = UDim.new(0, 8)
	modePad.PaddingBottom = UDim.new(0, 8)
	modePad.Parent        = modePanel
	local modeLay = Instance.new("UIListLayout")
	modeLay.Padding   = UDim.new(0, 6)
	modeLay.SortOrder = Enum.SortOrder.LayoutOrder
	modeLay.Parent    = modePanel
end

local modeRow = makeFrame(modePanel, {bg = C.PANEL, size = UDim2.new(1, 0, 0, 28), order = 1})
do
	local modeRowLay = Instance.new("UIListLayout")
	modeRowLay.FillDirection = Enum.FillDirection.Horizontal
	modeRowLay.Padding       = UDim.new(0, 6)
	modeRowLay.Parent        = modeRow
end

local simpleBtn = makeButton(modeRow, "Simple",
	{size = UDim2.new(0.48, 0, 1, 0), bg = C.ACCENT, tc = C.BG})
simpleBtn.LayoutOrder = 1

local volumeBtn = makeButton(modeRow, "Volume",
	{size = UDim2.new(0.48, 0, 1, 0), bg = C.BTN, tc = C.TEXT})
volumeBtn.LayoutOrder = 2

local modeDesc = makeLabel(modePanel, "Config will automatically select the mode", {
	color = C.DIMTEXT, size = 10, sz = UDim2.new(1, 0, 0, 24), order = 2, autosize = true
})

-- Step 5: Apply
makeSep(scroll, "5. Apply", 80)
local applyBtn = makeButton(scroll, "APPLY", {
	size = UDim2.new(1, 0, 0, 44), bg = C.GREEN, tc = C.BG, tsize = 15, order = 81
})

local statusBox = makeFrame(scroll, {bg = C.PANEL, size = UDim2.new(1, 0, 0, 80), order = 82, autosize = true})
do
	local statusPad = Instance.new("UIPadding")
	statusPad.PaddingLeft   = UDim.new(0, 8)
	statusPad.PaddingRight  = UDim.new(0, 8)
	statusPad.PaddingTop    = UDim.new(0, 8)
	statusPad.PaddingBottom = UDim.new(0, 8)
	statusPad.Parent        = statusBox
end
local statusLabel = makeLabel(statusBox, "Ready. Load JSON and click Apply.", {
	color = C.GREEN, size = 11, sz = UDim2.new(1, 0, 1, 0), autosize = true
})
statusLabel.TextWrapped    = true
statusLabel.TextYAlignment = Enum.TextYAlignment.Top

-- Quick guide
makeSep(scroll, "Quick Guide", 90)
local howto = makeFrame(scroll, {bg = C.PANEL, size = UDim2.new(1, 0, 0, 120), order = 91, autosize = true})
do
	local htPad = Instance.new("UIPadding")
	htPad.PaddingLeft   = UDim.new(0, 8)
	htPad.PaddingRight  = UDim.new(0, 8)
	htPad.PaddingTop    = UDim.new(0, 8)
	htPad.PaddingBottom = UDim.new(0, 8)
	htPad.Parent        = howto
	makeLabel(howto,
		"1. Run the Python analyzer to get JSON\n"
			.. "2. Paste JSON here and click Load JSON\n"
			.. "3. Select the face folder in Explorer\n"
			.. "4. Config is pre-filled -- click Apply Config\n"
			.. "5. Click APPLY\n"
			.. "6. Moon Animator 2 -> File -> Open\n\n"
			.. "Note: Supports texture-based faces only (not Dynamic Heads / FaceControls).",
		{color = C.DIMTEXT, size = 10, sz = UDim2.new(1, 0, 1, 0), autosize = true}
	)
end

-- ==============================================================
-- EVENT LOGIC
-- ==============================================================

local function switchMode(mode)
	state.mode = mode
	if mode == "simple" then
		simpleBtn.BackgroundColor3 = C.ACCENT
		simpleBtn.TextColor3       = C.BG
		volumeBtn.BackgroundColor3 = C.BTN
		volumeBtn.TextColor3       = C.TEXT
		modeDesc.Text = "Simple: one texture per phoneme"
	else
		simpleBtn.BackgroundColor3 = C.BTN
		simpleBtn.TextColor3       = C.TEXT
		volumeBtn.BackgroundColor3 = C.ACCENT
		volumeBtn.TextColor3       = C.BG
		modeDesc.Text = "Volume: separate textures for quiet / normal / loud"
	end
end

simpleBtn.MouseButton1Click:Connect(function() switchMode("simple") end)
volumeBtn.MouseButton1Click:Connect(function() switchMode("volume") end)

-- JSON
loadJsonBtn.MouseButton1Click:Connect(function()
	local raw = jsonBox.Text
	if raw == "" then
		jsonStatus.Text      = "JSON: empty!"
		jsonStatus.TextColor3 = C.RED
		return
	end

	local ok, data = pcall(function()
		return HttpService:JSONDecode(raw)
	end)

	if not ok or not data.keyframes then
		jsonStatus.Text       = "JSON: parse error!"
		jsonStatus.TextColor3 = C.RED
		state.jsonData        = nil
		return
	end

	state.jsonData = data
	local meta     = data.meta or {}
	local kfCount  = #data.keyframes

	if meta.fps then
		state.fps = meta.fps
	end

	jsonStatus.Text = string.format(
		"JSON: %d keyframes | FPS: %d | %s",
		kfCount,
		meta.fps or 24,
		meta.language or "?"
	)
	jsonStatus.TextColor3 = C.GREEN

	local hasVolume = data.volume_levels ~= nil
	if hasVolume then
		statusLabel.Text      = "JSON loaded (with volume). Click Apply."
		switchMode("volume")
	else
		statusLabel.Text      = "JSON loaded. Click Apply."
		switchMode("simple")
	end
	statusLabel.TextColor3 = C.ACCENT
end)

clearJsonBtn.MouseButton1Click:Connect(function()
	jsonBox.Text          = ""
	state.jsonData        = nil
	jsonStatus.Text       = "JSON: cleared"
	jsonStatus.TextColor3 = C.DIMTEXT
end)

-- Folder
pickFolderBtn.MouseButton1Click:Connect(function()
	local sel = Selection:Get()
	if #sel == 0 then
		folderStatus.Text       = "Nothing selected!"
		folderStatus.TextColor3 = C.RED
		return
	end
	local obj = sel[1]
	if obj.ClassName ~= "Folder" then
		folderStatus.Text       = "Select a Folder, not " .. obj.ClassName .. "!"
		folderStatus.TextColor3 = C.RED
		return
	end
	state.selectedFolder    = obj
	folderStatus.Text       = "Folder: " .. obj:GetFullName()
	folderStatus.TextColor3 = C.GREEN
	statusLabel.Text        = "Folder selected. Ready to Apply."
	statusLabel.TextColor3  = C.ACCENT
end)

-- Config
applyConfigBtn.MouseButton1Click:Connect(function()
	local text = configBox.Text
	if text == "" then
		configStatus.Text       = "Config is empty!"
		configStatus.TextColor3 = C.RED
		return
	end

	local count, errors = parseConfig(text)

	if count > 0 then
		configStatus.Text       = string.format("Applied %d settings", count)
		configStatus.TextColor3 = C.GREEN
		statusLabel.Text        = "Config applied. Click Apply to create keyframes."
		statusLabel.TextColor3  = C.GREEN

		local hasVolume = text:match("quiet") or text:match("loud")
		switchMode(hasVolume and "volume" or "simple")
	else
		configStatus.Text       = "Error: no settings recognized"
		configStatus.TextColor3 = C.RED
	end

	if #errors > 0 then
		statusLabel.Text       = "Some lines had errors:\n" .. table.concat(errors, "\n")
		statusLabel.TextColor3 = C.ORANGE
	end
end)

clearConfigBtn.MouseButton1Click:Connect(function()
	configBox.Text          = ""
	configStatus.Text       = "Config cleared"
	configStatus.TextColor3 = C.DIMTEXT
end)

-- Apply
applyBtn.MouseButton1Click:Connect(function()
	applyBtn.Text              = "Working..."
	applyBtn.BackgroundColor3  = C.YELLOW

	local ok, msg = applyLipSync()

	if ok then
		applyBtn.Text             = "Done!"
		applyBtn.BackgroundColor3 = C.GREEN
		statusLabel.Text          = msg
		statusLabel.TextColor3    = C.GREEN
	else
		applyBtn.Text             = "Error"
		applyBtn.BackgroundColor3 = C.RED
		statusLabel.Text          = msg
		statusLabel.TextColor3    = C.RED
	end

	task.delay(3, function()
		if applyBtn.Parent then
			applyBtn.Text             = "APPLY"
			applyBtn.BackgroundColor3 = C.GREEN
		end
	end)
end)

print("[AutoLipSync v4.1] Plugin loaded!")
print("  FIXED: Lua empty-string truthy bug in volume fallback")
print("  FIXED: TH viseme removed from config (Python never emits it)")
print("  Note: texture-based faces only -- no Dynamic Head / FaceControls support")
