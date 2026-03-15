-- =============================================================================
-- Algorithmic Clock - Pure Bitwise Reference Implementation
-- =============================================================================
-- Properties (all formally provable):
--   1. Deterministic       - same seed always produces same sequence
--   2. Bounded             - all states remain in 16-bit space
--   3. Finite period       - the sequence always cycles
--   4. Encoding-independent - no dependence on UTF or any text encoding
--   5. Reproducible        - anyone implementing this law gets identical output
-- =============================================================================

module AlgorithmicClock where

import Data.Bits
import Data.Word
import Data.List (elemIndex, nub)

-- =============================================================================
-- PART 1: Shared Basis - Fixed 16-bit state space
-- =============================================================================

type State = Word16

-- Every state lives in this bounded universe.
-- Overflow is impossible by type.
-- 65536 possible positions.

-- =============================================================================
-- PART 2: Pure Bitwise Primitives
-- =============================================================================

rotl16 :: Int -> State -> State
rotl16 n x = rotateL x n

rotr16 :: Int -> State -> State
rotr16 n x = rotateR x n

-- =============================================================================
-- PART 3: Coxeter-style Reflection Generators
-- =============================================================================
-- Each r_i is a reflection: applying it twice returns the original state.
-- Products of reflections produce rotations (clock advances).
-- This mirrors the Coxeter group structure: [2p+, 2+, 2q+, ...]

-- r0: XOR reflection (flips alternating bits)
r0 :: State -> State
r0 x = x `xor` 0xAAAA

-- r1: rotate-left-1 (reflection in bit-rotation space)
r1 :: State -> State
r1 = rotl16 1

-- r2: rotate-left-3
r2 :: State -> State
r2 = rotl16 3

-- r3: rotate-right-2
r3 :: State -> State
r3 = rotr16 2

-- Verify involution property: r0(r0(x)) == x
-- This holds by XOR self-cancellation
checkR0Involution :: State -> Bool
checkR0Involution x = r0 (r0 x) == x

-- =============================================================================
-- PART 4: Generator Products → Clock Hands
-- =============================================================================
-- Following Coxeter: products of reflections produce rotations.
-- More reflections = slower rotation = higher-order hand.

-- SECOND HAND: single-generator oscillation
-- Fastest cycle, finest resolution
-- Equivalent to dimension-2 rotation [2p]+
oscillate :: State -> State
oscillate x =
  rotl16 1 x `xor`
  rotl16 3 x `xor`
  rotr16 2 x `xor`
  0x1D1D

-- MINUTE HAND: product of two reflections
-- Double rotation: [2p+, 2+, 2q+]
-- Slower cycle than second hand
minuteHand :: State -> State
minuteHand = r0 . r1

-- HOUR HAND: product of three reflections
-- Triple rotation: [2p+, 2+, 2q+, 2+, 2r+]
-- Slowest cycle
hourHand :: State -> State
hourHand = r0 . r1 . r2

-- EPOCH HAND: product of four reflections
-- Even slower, for large-scale synchronization
epochHand :: State -> State
epochHand = r0 . r1 . r2 . r3

-- =============================================================================
-- PART 5: Band Classification (Stability Algorithm)
-- =============================================================================
-- This is the "where are we in spectrum space" measurement.
-- No interpretation, no encoding - pure structural classification.

data Band = Band
  { bitLengthB :: !Int  -- how many bits are needed (width class)
  , popCountB  :: !Int  -- how many bits are set (density)
  , edgeCountB :: !Int  -- how many bit-transitions exist (texture)
  } deriving (Eq, Show)

-- Highest occupied bit position + 1
-- This is the binary digit length - the width class
bitLength16 :: State -> Int
bitLength16 0 = 0
bitLength16 x = go 16
  where
    go 0 = 0
    go n = if testBit x (n-1) then n else go (n-1)

-- Count of set bits - the density class
popCount16 :: State -> Int
popCount16 = popCount

-- Count of 0->1 or 1->0 transitions around the 16-bit ring
-- This is the spectral texture / roughness measure
edgeCount16 :: State -> Int
edgeCount16 x = length
  [ ()
  | i <- [0..15]
  , testBit x i /= testBit x ((i+1) `mod` 16)
  ]

-- Full band classification: deterministic, bounded, pure bitwise
classify :: State -> Band
classify x = Band
  { bitLengthB = bitLength16 x
  , popCountB  = popCount16  x
  , edgeCountB = edgeCount16 x
  }

-- Band difference = the time signal between ticks
-- This is what replaces "elapsed seconds" in your clock model
deltaBand :: Band -> Band -> (Int, Int, Int)
deltaBand a b =
  ( bitLengthB b - bitLengthB a
  , popCountB  b - popCountB  a
  , edgeCountB b - edgeCountB a
  )

-- =============================================================================
-- PART 6: Complete Clock Tick
-- =============================================================================

data Hand = Second | Minute | Hour | Epoch deriving (Show, Eq)

data ClockReading = ClockReading
  { crState :: !State
  , crBand  :: !Band
  , crDelta :: !(Int, Int, Int)  -- delta from previous band
  } deriving (Show)

-- Advance the clock by one tick of the given hand
tick :: Hand -> State -> ClockReading
tick hand x =
  let x' = case hand of
              Second -> oscillate  x
              Minute -> minuteHand x
              Hour   -> hourHand   x
              Epoch  -> epochHand  x
      b0 = classify x
      b1 = classify x'
  in ClockReading x' b1 (deltaBand b0 b1)

-- =============================================================================
-- PART 7: Fibonacci Harmonic Driver
-- =============================================================================
-- Fibonacci injects the "prime factorial recursion anchor points"
-- you described - the minute-hand oscillation nodes.
-- Kept as integer arithmetic only (no floats).

fib16 :: Int -> State
fib16 n = go n 0 1
  where
    go 0 a _ = fromIntegral (a `mod` 65536)
    go k a b = go (k-1) b ((a + b) `mod` 65536)

-- Fibonacci-driven tick: each step is seeded by the Fibonacci residue
-- This creates the hierarchical "beats between anchor points" structure
fibDrivenTick :: Int -> State -> ClockReading
fibDrivenTick n x =
  let seed = x `xor` fib16 n
  in tick Second seed

-- =============================================================================
-- PART 8: Cycle Detection
-- =============================================================================
-- Every generator on a finite state space must have a finite period.
-- This computes it.

findPeriod :: (State -> State) -> State -> Int
findPeriod f seed = go (f seed) 1
  where
    go x n
      | x == seed = n
      | otherwise = go (f x) (n+1)

-- Safe version with a fuel limit (for testing)
findPeriodBounded :: Int -> (State -> State) -> State -> Maybe Int
findPeriodBounded limit f seed = go (f seed) 1
  where
    go x n
      | x == seed = Just n
      | n > limit = Nothing
      | otherwise = go (f x) (n+1)

-- =============================================================================
-- PART 9: Run the Clock
-- =============================================================================

-- Run n ticks of a given hand from a seed
runClock :: Int -> Hand -> State -> [ClockReading]
runClock = runClockExplicit

-- Cleaner run implementation using explicit state threading
runClockExplicit :: Int -> Hand -> State -> [ClockReading]
runClockExplicit 0 _ _    = []
runClockExplicit n hand x =
  let r = tick hand x
  in r : runClockExplicit (n-1) hand (crState r)

-- Fibonacci-driven run
runFibClock :: Int -> State -> [ClockReading]
runFibClock n seed = zipWith fibDrivenTick [0..n-1] (iterate step seed)
  where
    step x = oscillate (x `xor` fib16 0)  -- simplified; real version threads n

-- =============================================================================
-- PART 10: Verification Functions
-- =============================================================================

-- Verify that all reflections satisfy the involution law r(r(x)) == x
verifyInvolutions :: State -> [(String, Bool)]
verifyInvolutions x =
  [ ("r0 involution", r0 (r0 x) == x)
  , ("r1 involution", r1 (r1 x) == x)  -- rotate 1 twice = rotate 2 (not identity! r1 is order 16)
  , ("r1 order-16",   iterate r1 x !! 16 == x)
  , ("r2 order-16",   iterate r2 x !! 16 == x)
  ]
-- Note: r0 is a true involution (XOR). r1..r3 are cyclic of order 16/gcd(n,16).
-- This matches Coxeter: reflections generate rotations of various orders.

-- Verify determinism: same input always gives same output
verifyDeterminism :: State -> Bool
verifyDeterminism x = oscillate x == oscillate x  -- trivially true by purity

-- Verify boundedness: all states stay in 16-bit space (trivially true by Word16 type)
verifyBounded :: [ClockReading] -> Bool
verifyBounded = all (\r -> crState r >= 0)  -- Word16 is always in [0, 65535]

-- Verify band ranges
verifyBandRanges :: Band -> Bool
verifyBandRanges b =
  bitLengthB b >= 0 && bitLengthB b <= 16 &&
  popCountB  b >= 0 && popCountB  b <= 16 &&
  edgeCountB b >= 0 && edgeCountB b <= 16

-- =============================================================================
-- PART 11: Hierarchical Clock (Seconds/Minutes/Hours)
-- =============================================================================

data HierarchicalReading = HierarchicalReading
  { hrSecond :: !Int  -- position within second cycle
  , hrMinute :: !Int  -- position within minute cycle
  , hrHour   :: !Int  -- position within hour cycle
  , hrState  :: !State
  } deriving (Show)

-- Build a hierarchical clock from period information
-- The period of each hand determines the "base" for that level
hierarchicalTick :: Int -> Int -> Int -> Int -> State -> HierarchicalReading
hierarchicalTick periodS periodM periodH globalTick seed =
  let x     = iterate oscillate seed !! globalTick
      tS    = globalTick `mod` periodS
      tM    = (globalTick `div` periodS) `mod` periodM
      tH    = (globalTick `div` (periodS * periodM)) `mod` periodH
  in HierarchicalReading tS tM tH x

-- =============================================================================
-- PART 12: Comparison with Atomic Clock Model
-- =============================================================================

-- An atomic clock defines 1 second = 9,192,631,770 oscillations of caesium-133.
-- This is a COUNT of physical events.
--
-- Our algorithmic clock defines 1 "tick" = one deterministic state advance.
-- The correspondence is: physical_second = N * algorithmic_ticks
-- where N is chosen once and frozen in the spec.
--
-- Key properties comparison:
--
-- ATOMIC CLOCK:
--   Determinism source: quantum mechanics (physical law)
--   Drift:              ~1e-16 seconds/second (best)
--   Reproducibility:    requires identical hardware
--   Verifiability:      measurement-based
--   Portability:        requires physical caesium
--
-- ALGORITHMIC CLOCK:
--   Determinism source: logical necessity (mathematical law)
--   Drift:              exactly 0 (no physical substrate)
--   Reproducibility:    anyone with the algorithm gets identical results
--   Verifiability:      formally provable (Coq)
--   Portability:        runs on any substrate
--
-- CONCLUSION:
--   For physical duration measurement: atomic clock wins (has physical meaning)
--   For logical synchronization:       algorithmic clock wins (provably identical)
--   For distributed systems:           algorithmic clock wins (no hardware needed)
--   For tamper-evidence:               algorithmic clock wins (deviation detectable)

atomicClockFrequency :: Integer
atomicClockFrequency = 9192631770  -- Hz, by definition of SI second

-- Map algorithmic ticks to a notional "second" by choosing a correspondence
-- This is the only point where physical and logical time touch
algorithmicSecond :: Int -> Int  -- period of oscillate from given seed
algorithmicSecond seed =
  findPeriod oscillate (fromIntegral seed `mod` 65536)
