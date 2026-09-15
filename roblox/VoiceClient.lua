local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")

local API_URL = "https://YOUR-DOMAIN.com/roblox/player"

local function sendPlayerPosition(player)
	local character = player.Character
	if not character then return end

	local root = character:FindFirstChild("HumanoidRootPart")
	if not root then return end

	local position = root.Position

	local data = {
		user_id = player.UserId,
		x = position.X,
		y = position.Y,
		z = position.Z
	}

	local success, response = pcall(function()
		return HttpService:RequestAsync({
			Url = API_URL,
			Method = "POST",
			Headers = {
				["Content-Type"] = "application/json"
			},
			Body = HttpService:JSONEncode(data)
		})
	end)

	if not success then
		warn("MT Voice: Failed to send player position:", response)
	end
end

while true do
	for _, player in ipairs(Players:GetPlayers()) do
		sendPlayerPosition(player)
	end

	task.wait(1)
end
