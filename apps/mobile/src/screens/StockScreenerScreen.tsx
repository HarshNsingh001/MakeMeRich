import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { colors } from '../theme/colors';

export default function StockScreenerScreen({ navigation }: any) {
  return (
    <View style={styles.container}>
      <Text style={styles.header}>Stock Screener</Text>
      
      <View style={styles.strategies}>
        {['GARP', 'Value', 'Momentum', 'Quality'].map(s => (
          <TouchableOpacity key={s} style={styles.strategyBtn}>
            <Text style={styles.strategyText}>{s}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity 
        style={styles.demoRow}
        onPress={() => navigation.navigate('StockDetail', { symbol: 'TCS' })}
      >
        <Text style={styles.symbol}>TCS</Text>
        <Text style={styles.link}>View Analysis →</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary, padding: 20 },
  header: { fontSize: 24, fontWeight: 'bold', color: colors.textPrimary, marginBottom: 20 },
  strategies: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 30 },
  strategyBtn: { backgroundColor: colors.bgCard, borderWidth: 1, borderColor: colors.borderLight, paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20 },
  strategyText: { color: colors.textSecondary, fontWeight: '600' },
  demoRow: { flexDirection: 'row', justifyContent: 'space-between', padding: 16, backgroundColor: colors.bgCard, borderRadius: 12, borderWidth: 1, borderColor: colors.border },
  symbol: { color: colors.textPrimary, fontWeight: 'bold', fontSize: 16 },
  link: { color: colors.accentBlueBright, fontWeight: 'bold' }
});
