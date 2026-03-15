{-# LANGUAGE NumericUnderscores #-}
import Data.Bits
import Numeric (showHex, readHex)
import System.Environment (getArgs)

maskN :: Int -> Integer
maskN n = (1 `shiftL` n) - 1

rotlN :: Int -> Int -> Integer -> Integer
rotlN n k x = ((x `shiftL` km) .|. (x `shiftR` (n - km))) .&. maskN n
  where km = k `mod` n

rotrN :: Int -> Int -> Integer -> Integer
rotrN n k x = ((x `shiftR` km) .|. (x `shiftL` (n - km))) .&. maskN n
  where km = k `mod` n

constantN :: Int -> Integer
constantN n = foldl step 0 [1..(n `div` 8)]
  where step acc _ = (acc `shiftL` 8) .|. 0x1D

deltaN :: Int -> Integer -> Integer
deltaN n x = (rotlN n 1 x `xor` rotlN n 3 x `xor` rotrN n 2 x `xor` constantN n) .&. maskN n

bitLengthI :: Integer -> Int
bitLengthI 0 = 0
bitLengthI x = go 0 x
  where
    go c 0 = c
    go c v = go (c + 1) (v `shiftR` 1)

textureN :: Int -> Integer -> Int
textureN n x = length [() | i <- [0..(n-1)], testBit x i /= testBit x ((i+1) `mod` n)]

hexPad :: Int -> Integer -> String
hexPad n x = "0x" ++ replicate (n `div` 4 - length h) '0' ++ h
  where h = map toUpperHex (showHex x "")
        toUpperHex c = if c >= 'a' && c <= 'f' then toEnum (fromEnum c - 32) else c

stepJson :: Int -> Int -> Integer -> String
stepJson w i s =
  "{\"band\":{\"density\":" ++ show (popCount s) ++
  ",\"texture\":" ++ show (textureN w s) ++
  ",\"width\":" ++ show (bitLengthI s) ++
  "},\"state_hex\":\"" ++ hexPad w s ++
  "\",\"step\":" ++ show i ++ "}"

parseSeed :: String -> Integer
parseSeed seedStr
  | take 2 seedStr == "0x" || take 2 seedStr == "0X" = fst . head $ readHex (drop 2 seedStr)
  | otherwise = read seedStr

main :: IO ()
main = do
  args <- getArgs
  case args of
    [wStr, seedStr, stepsStr] -> do
      let w = read wStr :: Int
      let s0 = parseSeed seedStr .&. maskN w
      let steps = read stepsStr :: Int
      let states = take steps (iterate (deltaN w) s0)
      let rows = zipWith (stepJson w) [0..] states
      putStrLn $
        "{\"constant_hex\":\"" ++ hexPad w (constantN w) ++
        "\",\"seed_hex\":\"" ++ hexPad w s0 ++
        "\",\"steps\":[" ++ joinComma rows ++
        "],\"width\":" ++ show w ++ "}"
    _ -> error "usage: runhaskell oracle.hs <width> <seed> <steps>"

joinComma :: [String] -> String
joinComma [] = ""
joinComma [x] = x
joinComma (x:xs) = x ++ "," ++ joinComma xs
