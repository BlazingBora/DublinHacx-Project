import { StyleSheet, Text, View, Pressable } from "react-native";
import { colors, urgencyColor } from "../theme";

export default function ItemCard({ item, mode, selectable, selected, onToggleSelect }) {
  const borderColor = urgencyColor(item.urgency);

  return (
    <View style={[styles.card, { borderColor }]}>
      {selectable && !item.discard_tip && (
        <Pressable style={styles.selectRow} onPress={onToggleSelect} hitSlop={8}>
          <View style={[styles.checkbox, selected && styles.checkboxChecked]}>
            {selected && <Text style={styles.checkboxMark}>✓</Text>}
          </View>
          <Text style={styles.selectLabel}>use in recipe</Text>
        </Pressable>
      )}

      <Text style={styles.name}>{item.name || "Unknown"}</Text>

      {mode === "medication" ? (
        <>
          <Text style={styles.line}>Dosage: {item.dosage || "Unknown"}</Text>
          <Text style={styles.line}>Quantity: {item.quantity ?? "Unknown"}</Text>
          <Text style={[styles.line, styles.expiration, { color: borderColor }]}>
            {item.expiration_words}
          </Text>
          <Text style={styles.line}>
            Refills left: {item.refills_left ?? "Unknown"}
          </Text>
          {item.instructions ? (
            <Text style={styles.line}>Instructions: {item.instructions}</Text>
          ) : null}
        </>
      ) : (
        <>
          <Text style={styles.line}>Quantity: {item.quantity ?? 1}</Text>
          <Text style={styles.line}>
            Price: {item.price != null ? `$${Number(item.price).toFixed(2)}` : "Unknown"}
          </Text>
          <Text style={[styles.line, styles.expiration, { color: borderColor }]}>
            {item.expiration_words}
          </Text>
          <Text style={styles.line}>Storage: {item.storage || "Unknown"}</Text>
          {item.storage_tip ? (
            <Text style={[styles.line, styles.storageTip]}>💡 {item.storage_tip}</Text>
          ) : null}
          {item.freeze_tip ? (
            <Text style={[styles.line, styles.freezeTip]}>❄️ Freeze now to extend shelf life</Text>
          ) : null}
        </>
      )}

      {item.discard_tip ? (
        <Text style={[styles.line, styles.discardTip]}>
          ☠️ Expired. Throw this away, it's no longer safe.
        </Text>
      ) : item.stale_tip ? (
        <Text style={[styles.line, styles.staleTip]}>
          🍞 Past its date, still usable: {item.stale_tip}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  name: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 6,
  },
  line: {
    color: colors.muted,
    fontSize: 14,
    marginTop: 3,
  },
  expiration: {
    fontWeight: "700",
  },
  storageTip: {
    color: colors.accent,
  },
  freezeTip: {
    color: colors.freeze,
    fontWeight: "700",
  },
  discardTip: {
    color: colors.danger,
    fontWeight: "700",
  },
  staleTip: {
    color: colors.stale,
  },
  selectRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
    paddingVertical: 6,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.border,
    marginRight: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxChecked: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  checkboxMark: {
    color: colors.bg,
    fontSize: 12,
    fontWeight: "700",
  },
  selectLabel: {
    color: colors.muted,
    fontSize: 13,
  },
});
