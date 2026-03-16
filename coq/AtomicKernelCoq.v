(*
  Atomic Kernel Coq Companion.
  Normative core for deterministic replay artifact derivation.
*)

Require Import Coq.NArith.NArith.
Require Import Coq.Lists.List.
Import ListNotations.

Open Scope N_scope.

Definition mask (n : N) (x : N) : N :=
  N.land x (N.pred (N.pow 2 n)).

Definition rotl (n : N) (x : N) (k : N) : N :=
  let k' := N.modulo k n in
  mask n (N.lor (N.shiftl x k') (N.shiftr x (n - k'))).

Definition rotr (n : N) (x : N) (k : N) : N :=
  let k' := N.modulo k n in
  mask n (N.lor (N.shiftr x k') (N.shiftl x (n - k'))).

Fixpoint repeat_byte_1d_nat (m : nat) : N :=
  match m with
  | O => 0
  | S m' => N.lor (N.shiftl (repeat_byte_1d_nat m') 8) 29
  end.

Definition constant_of_width (n : N) : N :=
  repeat_byte_1d_nat (N.to_nat (N.div n 8)).

Definition delta (n : N) (x : N) : N :=
  mask n
    (N.lxor
      (N.lxor (N.lxor (rotl n x 1) (rotl n x 3)) (rotr n x 2))
      (constant_of_width n)).

Fixpoint replay_loop (steps : nat) (n : N) (x : N) : list N :=
  match steps with
  | O => []
  | S k => x :: replay_loop k n (delta n x)
  end.

Definition replay (n : N) (seed : N) (steps : nat) : list N :=
  replay_loop steps n (mask n seed).

Theorem delta_deterministic :
  forall n x y,
    x = y ->
    delta n x = delta n y.
Proof.
  intros n x y Hxy.
  rewrite Hxy.
  reflexivity.
Qed.

Theorem replay_deterministic :
  forall n steps seed1 seed2,
    seed1 = seed2 ->
    replay n seed1 steps = replay n seed2 steps.
Proof.
  intros n steps seed1 seed2 Hseed.
  rewrite Hseed.
  reflexivity.
Qed.

Theorem replay_loop_len :
  forall n steps x,
    length (replay_loop steps n x) = steps.
Proof.
  intros n steps.
  induction steps as [|k IH].
  - intro x. simpl. reflexivity.
  - intro x. simpl. rewrite IH. reflexivity.
Qed.

Theorem replay_len :
  forall n steps seed,
    length (replay n seed steps) = steps.
Proof.
  intros n steps seed.
  unfold replay.
  apply replay_loop_len.
Qed.

Definition W16 : N := 16.
Definition W32 : N := 32.
Definition W64 : N := 64.
Definition W128 : N := 128.
Definition W256 : N := 256.
