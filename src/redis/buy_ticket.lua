local stock = tonumber(redis.call("GET", KEYS[1]))

if stock == nil then
    return -1 
end

-- ATOMIC LOGIC
if stock > 0 then
    redis.call("DECR", KEYS[1])
    return 1 -- Ticket Booked Successfully 
else
    return 0 -- Sold Out
end