(* Algorithmic Clock Kernel
   Draft normative kernel.
*)

Require Import Coq.NArith.NArith.
Require Import Coq.Bool.Bool.
Require Import Coq.Lists.List.
Import ListNotations.

Open Scope N_scope.

Definition mask (n : N) (x : N) : N :=
  N.land x (N.pred (N.pow 2 n)).

Definition rotl (n : N) (x : N) (k : N) : N :=
  mask n (N.lor (N.shiftl x k) (N.shiftr x (n - k))).

Definition rotr (n : N) (x : N) (k : N) : N :=
  mask n (N.lor (N.shiftr x k) (N.shiftl x (n - k))).

Definition repeat_byte_1D (bytes : N) : N :=
  N.ones (8 * bytes) * 29 / 255.

(* The constant family is modeled operationally in fixtures and references.
   For the normative kernel, we provide a direct constructor from byte count. *)

Fixpoint repeat_1D_nat (m : nat) : N :=
  match m with
  | O => 0
  | S m' => N.lor (N.shiftl (repeat_1D_nat m') 8) 29
  end.

Definition constant_of_width (n : N) : N :=
  repeat_1D_nat (N.to_nat (N.div n 8)).

Definition delta (n : N) (x : N) : N :=
  mask n
    (N.lxor
      (N.lxor
        (N.lxor (rotl n x 1) (rotl n x 3))
        (rotr n x 2))
      (constant_of_width n)).

Definition width (x : N) : N :=
  if N.eqb x 0 then 0 else N.succ (N.log2 x).

Fixpoint popcount_fuel (fuel : nat) (x : N) : N :=
  match fuel with
  | O => 0
  | S f =>
      (if N.odd x then 1 else 0) +
      popcount_fuel f (N.div2 x)
  end.

Definition popcount (n : nat) (x : N) : N :=
  popcount_fuel n x.

Fixpoint edge_loop (i : nat) (n : nat) (x : N) : N :=
  match i with
  | O => 0
  | S i' =>
      let b0 := N.testbit x (N.of_nat i') in
      let b1 := N.testbit x (N.of_nat ((i' + 1) mod n)) in
      (if Bool.eqb b0 b1 then 0 else 1) + edge_loop i' n x
  end.

Definition edgecount (n : nat) (x : N) : N :=
  edge_loop n n x.

Record band := Band {
  w : N;
  d : N;
  e : N
}.

Definition classify (n : nat) (x : N) : band :=
  Band (width x) (popcount n x) (edgecount n x).

Fixpoint sequence (steps : nat) (n : N) (seed : N) : list N :=
  match steps with
  | O => []
  | S k => seed :: sequence k n (delta n seed)
  end.

Fixpoint readings (steps : nat) (n : N) (seed : N) : list band :=
  match steps with
  | O => []
  | S k => classify (N.to_nat n) seed :: readings k n (delta n seed)
  end.

Theorem delta_deterministic :
  forall n x y,
    x = y ->
    delta n x = delta n y.
Proof.
  intros n x y H.
  rewrite H.
  reflexivity.
Qed.

Theorem classify_deterministic :
  forall n x y,
    x = y ->
    classify n x = classify n y.
Proof.
  intros n x y H.
  rewrite H.
  reflexivity.
Qed.

Theorem sequence_deterministic :
  forall steps n x y,
    x = y ->
    sequence steps n x = sequence steps n y.
Proof.
  intros steps n x y H.
  rewrite H.
  reflexivity.
Qed.

Theorem readings_deterministic :
  forall steps n x y,
    x = y ->
    readings steps n x = readings steps n y.
Proof.
  intros steps n x y H.
  rewrite H.
  reflexivity.
Qed.

Definition W16  : N := 16.
Definition W32  : N := 32.
Definition W64  : N := 64.
Definition W128 : N := 128.
Definition W256 : N := 256.
