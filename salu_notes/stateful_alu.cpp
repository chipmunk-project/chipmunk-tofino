/* Copyright 2013-present Barefoot Networks, Inc.
 */

#include "stateful_alu.h"
#include "stateful_alu_testing.h"

#include <bm/bm_sim/extern.h>
#include <bm/bm_sim/P4Objects.h>

#include <boost/functional/hash.hpp>

#include <string>
#include <array>
#include <vector>
#include <sstream>  // std::stringstream
#include <algorithm>  // std::transform
#include <set>
#include <unordered_map>
#include <mutex>

using bm::Field;
using bm::RegisterArray;
using bm::ExternType;
using bm::Data;
using bm::Expression;
using bm::NamedCalculation;
using bm::MatchTableIndirectWS;
using bm::ActionProfile;

namespace {

using GroupSelectionIface = ActionProfile::GroupSelectionIface;

class GroupMembershipMgr :
      public GroupMembershipMgrIface, public GroupSelectionIface {
 public:
  using mbr_hdl_t = ActionProfile::mbr_hdl_t;
  using grp_hdl_t = ActionProfile::grp_hdl_t;
  using Index = uint32_t;

  explicit GroupMembershipMgr(RegisterArray *reg)
      : reg(reg) {
    // register callback for stateful writes
    reg->register_notifier(
        [this](size_t index) { this->register_notify(index); });
  }

  // TODO(unknown): for these functions, handle gracefully the case where the
  // grp, mbr pair is not valid
  Index get_assigned_index(grp_hdl_t grp, mbr_hdl_t mbr) const override {
    std::lock_guard<std::mutex> lock(mutex);
    return map_mbr_to_index.at(Mbr(grp, mbr));
  }

  void activate_member(grp_hdl_t grp, mbr_hdl_t mbr) override {
    Index index;
    {
      std::lock_guard<std::mutex> lock(mutex);
      index = map_mbr_to_index.at(Mbr(grp, mbr));
    }
    auto r_lock = reg->unique_lock();
    reg->at(index).set(1);
  }

  void deactivate_member(grp_hdl_t grp, mbr_hdl_t mbr) override {
    Index index;
    {
      std::lock_guard<std::mutex> lock(mutex);
      index = map_mbr_to_index.at(Mbr(grp, mbr));
    }
    auto r_lock = reg->unique_lock();
    reg->at(index).set(0);
  }

 private:
  struct Mbr {
    Mbr(grp_hdl_t grp, mbr_hdl_t mbr)
        : grp(grp), mbr(mbr) { }

    bool operator==(const Mbr &other) const {
      return (grp == other.grp) && (mbr == other.mbr);
    }

    bool operator!=(const Mbr &other) const {
      return !(*this == other);
    }

    grp_hdl_t grp;
    mbr_hdl_t mbr;
  };

  struct MbrHash {
    size_t operator()(const Mbr &m) const {
      size_t seed = 0;
      boost::hash_combine(seed, m.grp);
      boost::hash_combine(seed, m.mbr);
      return seed;
    }
  };

  using hash_t = ActionProfile::hash_t;

  void add_member_to_group(grp_hdl_t grp, mbr_hdl_t mbr) override {
    Index new_index;
    {
      std::lock_guard<std::mutex> lock(mutex);
      // construct if does not exist
      auto &indexes = group_indexes[grp];
      bm::handle_t new_index_;
      assert(!index_mgr.get_handle(&new_index_));
      new_index = static_cast<Index>(new_index_);
      indexes.insert(new_index);
      map_mbr_to_index.emplace(Mbr(grp, mbr), new_index);
      map_index_to_mbr.emplace(new_index, Mbr(grp, mbr));
    }
    // activate member
    auto r_lock = reg->unique_lock();
    reg->at(new_index).set(1);
  }

  void remove_member_from_group(grp_hdl_t grp, mbr_hdl_t mbr) override {
    Index index;
    {
      std::lock_guard<std::mutex> lock(mutex);
      auto &indexes = group_indexes.at(grp);
      index = map_mbr_to_index.at(Mbr(grp, mbr));
      assert(indexes.erase(index) > 0);
      assert(!index_mgr.release_handle(index));
      map_mbr_to_index.erase(Mbr(grp, mbr));
      map_index_to_mbr.erase(index);
    }
    // deactivate member
    auto r_lock = reg->unique_lock();
    reg->at(index).set(0);
  }

  // this needs to return a member based on which members are activated and the
  // hash-computed index parameter
  mbr_hdl_t get_from_hash(grp_hdl_t grp, hash_t h) const override {
    std::lock_guard<std::mutex> lock(mutex);
    auto r_lock = reg->unique_lock();
    const auto &indexes = group_indexes.at(grp);
    size_t active_count = 0;
    for (auto i : indexes)
      if (reg->at(i).get<int>() > 0) active_count++;
    auto index = static_cast<Index>(h % active_count);
    for (auto i : indexes) {
      if (reg->at(i).get<int>() > 0) {
        if (index-- == 0) {
          auto mbr = map_index_to_mbr.at(i);
          assert(mbr.grp == grp);
          return mbr.mbr;
        }
      }
    }
    assert(0);
    return 0;
  }

  void reset() override {
    std::lock_guard<std::mutex> lock(mutex);
    map_mbr_to_index.clear();
    map_index_to_mbr.clear();
    group_indexes.clear();
    index_mgr.clear();
    // probably not necessary to reset the state of the register array here, as
    // it is probably taken care of somewhere else
  }

  // when this method is called, the Register lock is always held
  void register_notify(size_t idx) {
    (void) idx;
    // TODO(unknown): we don't use this information at this stage to make the
    // implementation easier. If the code turns out to be too slow (because
    // scanning the register array looking for an active member is indeed pretty
    // slow as groups grow bigger), this function can be implemented properly.
  }

  RegisterArray *reg;
  mutable std::mutex mutex{};
  std::unordered_map<Mbr, Index, MbrHash> map_mbr_to_index{};
  std::unordered_map<Index, Mbr> map_index_to_mbr{};
  using GroupIndexes = std::set<Index>;
  std::unordered_map<grp_hdl_t, GroupIndexes> group_indexes{};
  bm::HandleMgr index_mgr{};
};

}  // namespace

// this implementation of statefule ALU is not complete, in particular it does
// not support single-bit mode.
class stateful_alu : public ExternType, public StatefulALUIface {
 public:
  BM_EXTERN_ATTRIBUTES {
    BM_EXTERN_ATTRIBUTE_ADD(reg);
    BM_EXTERN_ATTRIBUTE_ADD(selector_binding);
    BM_EXTERN_ATTRIBUTE_ADD(initial_register_lo_value);
    BM_EXTERN_ATTRIBUTE_ADD(initial_register_hi_value);
    BM_EXTERN_ATTRIBUTE_ADD(condition_hi);
    BM_EXTERN_ATTRIBUTE_ADD(condition_lo);
    BM_EXTERN_ATTRIBUTE_ADD(update_lo_1_predicate);
    BM_EXTERN_ATTRIBUTE_ADD(update_lo_1_value);
    BM_EXTERN_ATTRIBUTE_ADD(update_lo_2_predicate);
    BM_EXTERN_ATTRIBUTE_ADD(update_lo_2_value);
    BM_EXTERN_ATTRIBUTE_ADD(update_hi_1_predicate);
    BM_EXTERN_ATTRIBUTE_ADD(update_hi_1_value);
    BM_EXTERN_ATTRIBUTE_ADD(update_hi_2_predicate);
    BM_EXTERN_ATTRIBUTE_ADD(update_hi_2_value);
    BM_EXTERN_ATTRIBUTE_ADD(output_predicate);
    BM_EXTERN_ATTRIBUTE_ADD(output_value);
    BM_EXTERN_ATTRIBUTE_ADD(output_dst);
    BM_EXTERN_ATTRIBUTE_ADD(math_unit_input);
    BM_EXTERN_ATTRIBUTE_ADD(math_unit_output_scale);
    BM_EXTERN_ATTRIBUTE_ADD(math_unit_exponent_shift);
    BM_EXTERN_ATTRIBUTE_ADD(math_unit_exponent_invert);
    BM_EXTERN_ATTRIBUTE_ADD(math_unit_lookup_table);
    BM_EXTERN_ATTRIBUTE_ADD(reduction_or_group);
    BM_EXTERN_ATTRIBUTE_ADD(stateful_logging_mode);
    // not part of the P4, but needed from the compiler (and part of the JSON)
    BM_EXTERN_ATTRIBUTE_ADD(_dual_width_);
    BM_EXTERN_ATTRIBUTE_ADD(_bitwidth_);
    BM_EXTERN_ATTRIBUTE_ADD(_master_);
  }

  void init() override {
    if (_dual_width_ == "True")
      dual_width_mode = true;
    bitwidth = std::stoi(_bitwidth_);
    if (_master_ == "True")
      master = true;

    reg_v = get_p4objects().get_register_array(reg);

    if (!selector_binding.empty()) {
      // TODO(antonin)
      // we retrieve the appropriate indirect table with selector, but we don't
      // use it yet. In Tofino, the stateful ALU can be used by the data plane
      // to deactivate members of a group. This requires changes to bmv2 so that
      // a register can be used to store group membership information.
      auto table = get_p4objects().get_abstract_match_table(selector_binding);
      selector_binding_v = dynamic_cast<decltype(selector_binding_v)>(table);
      assert(selector_binding_v != nullptr);  // checked by compiler
      if (master) {
        group_membership_mgr.reset(new GroupMembershipMgr(reg_v));
        selector_binding_v->get_action_profile()->set_group_selector(
            group_membership_mgr.get());
      }
    }

    if (math_unit_exponent_invert == "True")
      math_unit_exponent_invert_v = true;

    if (!math_unit_lookup_table.empty()) {
      std::stringstream sstream(math_unit_lookup_table);
      std::string item;
      std::vector<std::string> tokens;
      while (std::getline(sstream, item, ' '))
        tokens.push_back(item);
      assert(tokens.size() != math_unit_lookup_table_v.size());
      std::transform(
          tokens.begin(), tokens.end(), math_unit_lookup_table_v.begin(),
          [](const std::string s) { return std::stoi(s, nullptr, 0); } );
    }

    if (stateful_logging_mode == "table_hit")
      stafeful_logging_mode_v = LoggingMode::TABLE_HIT;
    else if (stateful_logging_mode == "table_miss")
      stafeful_logging_mode_v = LoggingMode::TABLE_MISS;
    else if (stateful_logging_mode == "gateway_inhibit")
      stafeful_logging_mode_v = LoggingMode::GATEWAY_INHIBIT;
    else if (stateful_logging_mode == "address")
      stafeful_logging_mode_v = LoggingMode::ADDRESS;

    for (size_t i = 0; i < reg_v->size(); i++) {
      write_to_register(i, initial_register_lo_value.get<RegisterV>(),
                        initial_register_hi_value.get<RegisterV>());
    }
  }

  void execute_stateful_alu_w_index(const Data &index) {
    return execute(index.get<size_t>());
  }

  void execute_stateful_alu() {
    return execute(get_packet().get_entry_index());
  }

  void execute_stateful_alu_from_hash(const NamedCalculation &hash) {
    auto index = hash.output(get_packet()) % reg_v->size();
    return execute(index);
  }

  void execute_stateful_log() {
    // TODO(unknown)
    assert(0);
  }

 private:
  using RegisterV = uint32_t;

  bool is_master() const override { return master; }

  bool is_bound_to_selector() const override {
    return selector_binding_v != nullptr;
  }

  GroupMembershipMgrIface *get_group_membership_mgr() override {
    // nullptr if this instance is not "master"
    return group_membership_mgr.get();
  }

  Field *output_dst_f() const {
    auto phv = get_packet().get_phv();
    if (output_dst.empty()) return nullptr;
    auto &output_f = phv->get_field(output_dst);
    output_f.set_arith(true);
    return &output_f;
  }

  void write_to_register(size_t index, RegisterV lo, RegisterV hi = 0) const {
    auto &r = reg_v->at(index);
    uint64_t v = lo;
    if (dual_width_mode)
      v |= (static_cast<decltype(v)>(hi) << (bitwidth / 2));
    r.set(v);
  }

  void read_from_register(size_t index, RegisterV *lo,
                          RegisterV *hi = nullptr) const {
    const auto &r = reg_v->at(index);
    auto v = r.get<uint64_t>();
    if (dual_width_mode && hi != nullptr) {
      uint64_t lo_mask = (static_cast<decltype(v)>(1) << (bitwidth / 2)) - 1;
      *lo = v & lo_mask;
      *hi = v >> (bitwidth / 2);
    } else {
      *lo = v;
    }
  }

  int compute_predicate(bool cond_hi, bool cond_lo) const {
    if (cond_hi && cond_lo)
      return 8;
    else if (cond_hi)
      return 4;
    else if (cond_lo)
      return 2;
    return 1;
  }

  // perform reduction-or: if we are the first sALU in the group to be executed,
  // we overwrite the field with the output value, otherwise we OR the output
  // value with the current value of the field
  void do_reduction_or(const Data &output_v, Field *output_f) const {
    auto phv = get_packet().get_phv();
    auto &or_group_scratch = phv->get_field(reduction_or_group);
    or_group_scratch.set_arith(true);
    const auto first_sALU_in_or_group = (or_group_scratch.get<int>() == 0);
    if (first_sALU_in_or_group) {
      or_group_scratch.set(1);
      output_f->set(output_v);
    } else {
      output_f->bit_or(*output_f, output_v);
    }
  }

  void execute_gen(size_t index) {
    RegisterV lo(0), hi(0);
    read_from_register(index, &lo, &hi);
    std::vector<Data> locals_registers;
    locals_registers.emplace_back(lo);
    locals_registers.emplace_back(hi);

    // evaluate conditions
    auto phv = get_packet().get_phv();
    auto cond_lo = condition_lo.eval_bool(*phv, locals_registers);
    auto cond_hi = condition_hi.eval_bool(*phv, locals_registers);
    std::vector<Data> locals_conditions;
    locals_conditions.emplace_back(cond_lo);
    locals_conditions.emplace_back(cond_hi);

    // if predicate and update are omitted in the P4, no-op
    // if only the predicate is omitted, the update is always applied
    // because an "empty" Expression evaluates to 0, if the update is omitted
    // (but not the predicate), the update will be 0
    auto eval_predicate = [&locals_conditions, phv](const Expression &predicate,
                                                    const Expression &update) {
      if (predicate.empty() && update.empty()) return false;
      if (predicate.empty()) return true;
      return predicate.eval_bool(*phv, locals_conditions);
    };

    // evaluate predicates
    auto pred_lo_1 = eval_predicate(update_lo_1_predicate, update_lo_1_value);
    auto pred_lo_2 = eval_predicate(update_lo_2_predicate, update_lo_2_value);
    auto pred_hi_1 = eval_predicate(update_hi_1_predicate, update_hi_1_value);
    auto pred_hi_2 = eval_predicate(update_hi_2_predicate, update_hi_2_value);

    // compute updates
    // reserve space for alu_lo, alu_hi, register_lo, register_hi, predicate and
    // combined predicate
    std::vector<Data> locals_output(6);
    auto &alu_lo = locals_output[0];
    auto &alu_hi = locals_output[1];
    auto &register_lo = locals_output[2];
    auto &register_hi = locals_output[3];
    auto &predicate = locals_output[4];
    auto &combined_predicate = locals_output[5];
    Data tmp1(0), tmp2(0);
    if (pred_lo_1) update_lo_1_value.eval_arith(*phv, &tmp1, locals_registers);
    if (pred_lo_2) update_lo_2_value.eval_arith(*phv, &tmp2, locals_registers);
    if (pred_lo_1 || pred_lo_2)
      alu_lo.bit_or(tmp1, tmp2);
    else
      alu_lo.set(lo);
    tmp1.set(0);
    tmp2.set(0);
    if (pred_hi_1) update_hi_1_value.eval_arith(*phv, &tmp1, locals_registers);
    if (pred_hi_2) update_hi_2_value.eval_arith(*phv, &tmp2, locals_registers);
    if (pred_hi_1 || pred_hi_2)
      alu_hi.bit_or(tmp1, tmp2);
    else
      alu_hi.set(hi);

    auto output_f = output_dst_f();
    if (output_f) {
      auto pred_output = eval_predicate(output_predicate, output_value);
      if (pred_output) {
        register_lo.set(lo);
        register_hi.set(hi);
        combined_predicate.set(1);  // by definition of combined_predicate
        predicate.set(compute_predicate(cond_hi, cond_lo));
        if (reduction_or_group.empty()) {
          output_value.eval_arith(*phv, output_f, locals_output);
        } else {
          output_value.eval_arith(*phv, &tmp1, locals_output);
          do_reduction_or(tmp1, output_f);
        }
      }
    }

    // finally update registers
    write_to_register(index, alu_lo.get<RegisterV>(), alu_hi.get<RegisterV>());
  }

  void execute_1b(size_t index) {
    auto phv = get_packet().get_phv();

    RegisterV bit(0);
    read_from_register(index, &bit);
    assert(bit == 0 || bit == 1);

    std::vector<Data> locals(8);
    auto &set_bit = locals[2];
    auto &set_bitc = locals[3];
    auto &clr_bit = locals[4];
    auto &clr_bitc = locals[5];
    auto &read_bit = locals[6];
    auto &read_bitc = locals[7];

    // for update
    set_bit.set(1);
    set_bitc.set(1);
    clr_bit.set(0);
    clr_bitc.set(0);
    read_bit.set(bit);
    read_bitc.set(bit);
    update_lo_1_value.eval_arith(*phv, &reg_v->at(index), locals);

    auto output_f = output_dst_f();
    if (output_f) {
      // for output
      RegisterV cbit = (bit == 0) ? 1 : 0;
      set_bit.set(bit);
      set_bitc.set(cbit);
      clr_bit.set(bit);
      clr_bitc.set(cbit);
      read_bit.set(bit);
      read_bitc.set(cbit);
      // reuse locals
      auto &alu_lo = locals[0];
      update_lo_1_value.eval_arith(*phv, &alu_lo, locals);
      // for tofino, register_lo can only be used with 'read' operations, but we
      // don't enforce it here
      auto &register_lo = locals[2];
      register_lo.set(bit);
      if (reduction_or_group.empty()) {
        output_value.eval_arith(*phv, output_f, locals);
      } else {
        Data tmp;
        output_value.eval_arith(*phv, &tmp, locals);
        do_reduction_or(tmp, output_f);
      }
    }
  }

  bool is_single_bit() const {
    return (bitwidth == 1);
  }

  void execute(size_t index) {
    // action primitives lock register arrays which are used as parameters, but
    // this register is never used as a parameter for this extern's methods, so
    // no risk of requesting the lock twice.
    auto lock = reg_v->unique_lock();
    if (is_single_bit())
      execute_1b(index);
    else
      execute_gen(index);
  }

  // declared attribute
  std::string reg{};
  std::string selector_binding{};
  Data initial_register_lo_value{0};
  Data initial_register_hi_value{0};
  Expression condition_hi{};
  Expression condition_lo{};
  Expression update_lo_1_predicate{};
  Expression update_lo_1_value{};
  Expression update_lo_2_predicate{};
  Expression update_lo_2_value{};
  Expression update_hi_1_predicate{};
  Expression update_hi_1_value{};
  Expression update_hi_2_predicate{};
  Expression update_hi_2_value{};
  Expression output_predicate{};
  Expression output_value{};
  std::string output_dst{};
  Expression math_unit_input{};
  Data math_unit_output_scale{0};
  Data math_unit_exponent_shift{0};
  std::string math_unit_exponent_invert{};
  std::string math_unit_lookup_table{};
  // if the sALU is part of a reduction group, this is the name of a scratch
  // metadata field which we use to keep track of whether the output field has
  // been zeroed out yet
  std::string reduction_or_group{};
  std::string stateful_logging_mode{};
  std::string _dual_width_{};
  std::string _bitwidth_{};
  std::string _master_{};

  enum class LoggingMode {
    NONE, TABLE_HIT, TABLE_MISS, GATEWAY_INHIBIT, ADDRESS
  };

  // implementation members
  RegisterArray *reg_v{nullptr};
  MatchTableIndirectWS *selector_binding_v{nullptr};
  bool math_unit_exponent_invert_v{false};
  std::array<uint8_t, 16> math_unit_lookup_table_v{};
  LoggingMode stafeful_logging_mode_v{LoggingMode::NONE};
  bool dual_width_mode{false};
  size_t bitwidth{};
  bool master{false};
  std::unique_ptr<GroupMembershipMgr> group_membership_mgr{nullptr};
};


BM_REGISTER_EXTERN(stateful_alu);
BM_REGISTER_EXTERN_METHOD(stateful_alu, execute_stateful_alu_w_index,
                          const Data &);
BM_REGISTER_EXTERN_METHOD(stateful_alu, execute_stateful_alu);
BM_REGISTER_EXTERN_METHOD(stateful_alu, execute_stateful_alu_from_hash,
                          const NamedCalculation &);
// TODO(unknown): expose when ready
// BM_REGISTER_EXTERN_METHOD(stateful_alu, execute_stateful_log);

StatefulALUIface *
StatefulALUIface::cast_instance(ExternType *extern_instance) {
  return static_cast<StatefulALUIface *>(
      dynamic_cast<stateful_alu *>(extern_instance));
}

// dummy function, which ensures that this unit is not discarded by the linker
// it is being called by the constructor of TofinoSwitch
int import_stateful_alu() { return 0; }

namespace testing {

GroupSelectionIface *cast_group_membership_mgr(GroupMembershipMgrIface *mgr) {
  return static_cast<GroupSelectionIface *>(
      dynamic_cast<GroupMembershipMgr *>(mgr));
}

}  // namespace testing
