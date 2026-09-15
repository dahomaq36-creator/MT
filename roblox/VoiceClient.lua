local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")

local API_URL = "https://mt-o8ez.onrender.com"


-- =====================================================
-- إرسال موقع اللاعب للسيرفر
-- =====================================================

local function sendPlayerPosition(player)

	local character = player.Character

	if not character then
		return
	end

	local root = character:FindFirstChild("HumanoidRootPart")

	if not root then
		return
	end

	local position = root.Position

	local data = {
		user_id = player.UserId,
		x = position.X,
		y = position.Y,
		z = position.Z
	}

	local success, response = pcall(function()

		return HttpService:RequestAsync({
			Url = API_URL .. "/roblox/player",
			Method = "POST",

			Headers = {
				["Content-Type"] = "application/json"
			},

			Body = HttpService:JSONEncode(data)
		})

	end)

	if not success then

		warn(
			"MT Voice: Failed to send player position:",
			response
		)

	end

end


-- =====================================================
-- فحص رمز التحقق
-- =====================================================

local function checkVerificationCode(player)

	local success, response = pcall(function()

		return HttpService:GetAsync(
			API_URL ..
			"/roblox/verification/" ..
			tostring(player.UserId)
		)

	end)

	if not success then
		return
	end


	local decodeSuccess, data = pcall(function()

		return HttpService:JSONDecode(response)

	end)

	if not decodeSuccess then
		return
	end


	if not data.pending then
		return
	end


	local code = data.code


	-- =================================================
	-- PLAYER GUI
	-- =================================================

	local playerGui = player:FindFirstChild("PlayerGui")

	if not playerGui then
		return
	end


	local oldGui =
		playerGui:FindFirstChild("MTVoiceVerification")


	if oldGui then

		local codeLabel =
			oldGui:FindFirstChild(
				"CodeLabel",
				true
			)

		if codeLabel then

			codeLabel.Text =
				"رمز MT Voice: " .. code

		end

		return

	end


	-- =================================================
	-- إنشاء واجهة الرمز
	-- =================================================

	local screenGui =
		Instance.new("ScreenGui")

	screenGui.Name =
		"MTVoiceVerification"

	screenGui.ResetOnSpawn = false

	screenGui.Parent = playerGui


	local frame =
		Instance.new("Frame")

	frame.Size =
		UDim2.new(0, 360, 0, 150)

	frame.Position =
		UDim2.new(0.5, -180, 0.15, 0)

	frame.BackgroundColor3 =
		Color3.fromRGB(25, 25, 25)

	frame.BorderSizePixel = 0

	frame.Parent = screenGui


	local corner =
		Instance.new("UICorner")

	corner.CornerRadius =
		UDim.new(0, 12)

	corner.Parent = frame


	local title =
		Instance.new("TextLabel")

	title.Size =
		UDim2.new(1, 0, 0, 40)

	title.Position =
		UDim2.new(0, 0, 0, 5)

	title.BackgroundTransparency = 1

	title.Text = "🔐 MT Voice"

	title.TextColor3 =
		Color3.fromRGB(255, 255, 255)

	title.TextScaled = true

	title.Font =
		Enum.Font.GothamBold

	title.Parent = frame


	local codeLabel =
		Instance.new("TextLabel")

	codeLabel.Name =
		"CodeLabel"

	codeLabel.Size =
		UDim2.new(1, -20, 0, 55)

	codeLabel.Position =
		UDim2.new(0, 10, 0, 50)

	codeLabel.BackgroundTransparency = 1

	codeLabel.Text =
		"رمز MT Voice: " .. code

	codeLabel.TextColor3 =
		Color3.fromRGB(255, 255, 255)

	codeLabel.TextScaled = true

	codeLabel.Font =
		Enum.Font.GothamBold

	codeLabel.Parent = frame


	local info =
		Instance.new("TextLabel")

	info.Size =
		UDim2.new(1, -20, 0, 30)

	info.Position =
		UDim2.new(0, 10, 0, 108)

	info.BackgroundTransparency = 1

	info.Text =
		"اكتب الرمز في موقع MT Voice - صالح لمدة 10 دقائق"

	info.TextColor3 =
		Color3.fromRGB(180, 180, 180)

	info.TextScaled = true

	info.Font =
		Enum.Font.Gotham

	info.Parent = frame

end


-- =====================================================
-- LOOP
-- =====================================================

while true do

	for _, player in ipairs(
		Players:GetPlayers()
	) do

		sendPlayerPosition(player)

		checkVerificationCode(player)

	end

	task.wait(1)

end
