import { useRef } from "react";
import { ActivityIndicator, Animated, Pressable, StyleSheet, Text } from "react-native";
import { colors } from "../theme";

export default function LoadingButton({ label, loadingLabel, loading, onPress, style, variant = "primary" }) {
  const scale = useRef(new Animated.Value(1)).current;

  const animateTo = (value) => {
    Animated.spring(scale, {
      toValue: value,
      useNativeDriver: true,
      speed: 40,
      bounciness: 0,
    }).start();
  };

  return (
    <Pressable
      disabled={loading}
      onPress={onPress}
      onPressIn={() => animateTo(0.97)}
      onPressOut={() => animateTo(1)}
    >
      <Animated.View
        style={[
          styles.button,
          variant === "secondary" && styles.secondary,
          loading && styles.disabled,
          { transform: [{ scale }] },
          style,
        ]}
      >
        {loading && (
          <ActivityIndicator
            size="small"
            color={variant === "secondary" ? colors.accent : colors.bg}
            style={styles.spinner}
          />
        )}
        <Text style={[styles.label, variant === "secondary" && styles.secondaryLabel]}>
          {loading ? loadingLabel : label}
        </Text>
      </Animated.View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.accent,
    borderRadius: 10,
    paddingVertical: 14,
    paddingHorizontal: 20,
  },
  secondary: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  disabled: {
    opacity: 0.7,
  },
  label: {
    color: colors.bg,
    fontWeight: "700",
    fontSize: 16,
  },
  secondaryLabel: {
    color: colors.text,
  },
  spinner: {
    marginRight: 8,
  },
});
